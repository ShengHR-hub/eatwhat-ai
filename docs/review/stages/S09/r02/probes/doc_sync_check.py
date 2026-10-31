"""v2.3.4 文档同步核查：旧口径残留、业务代码/DB/admin 保护。只读。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"

LIVE = [
    "MASTER_SPEC.md", "DASHBOARD_EXPANSION.md", "AGENTS.md", "docs/README.md",
    "docs/AGENT_MEMORY.md", "docs/review/STAGE_STATUS.md",
    "docs/review/stages/S09/r02/DECISIONS.md",
    "docs/review/stages/S09/r02/DATA_PLAN.md",
    "docs/review/stages/S09/r02/CONTRACT_MATRIX.md",
    "docs/review/stages/S09/r02/EXPERIMENT_PROTOCOL.md",
    "docs/review/stages/S09/r02/SUBMISSION.md",
    "docs/review/stages/S09/r02/BASELINE.md",
    "docs/review/stages/S09/r02/CHECKS.md",
]
TERMS = {
    "actual_1700": ("1700", ["原规格", "原目标", "不是", "非", "目标", "调研", "未达", "反推", "纠错", "禁止", "当实际数"]),
    "rule_2km": ("2km", ["作废", "旧", "不再", "不得", "纠错", "不是"]),
    "stats_12": ("12 个", []),
    "hard_60000": ("60,000+", ["不再", "不设", "除非", "若要", "按实际", "不能写", "不是当前实际", "原目标", "不固定"]),
    "actual_1500_siyuan": ("1500+", ["目标", "未达", "待", "不假设"]),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(path: Path):
    hits = {k: [] for k in TERMS}
    for no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        for key, (term, exemptions) in TERMS.items():
            if term in line and not any(x in line for x in exemptions):
                # 对 actual_1500_siyuan 只算思源上下文
                if key == "actual_1500_siyuan" and "思源" not in line:
                    continue
                hits[key].append({"line": no, "text": line.strip()[:260]})
    return {k: v for k, v in hits.items() if v}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    report = {"checked_at": "2026-10-25T00:00:00+08:00", "live": {}, "historical": {}, "protection": {}}
    for rel in LIVE:
        p = ROOT / rel
        if p.exists():
            hits = scan(p)
            if hits:
                report["live"][rel] = hits

    hist_terms = ["1700", "2km", "12 个", "60,000+", "1500+"]
    hist = {}
    for p in (ROOT / "docs/review/stages/S09/r01").rglob("*.md"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        found = {t: text.count(t) for t in hist_terms if t in text}
        if found:
            hist[str(p.relative_to(ROOT)).replace("\\", "/")] = found
    report["historical"]["S09/r01_preserved"] = hist

    # 业务代码哈希保护：只比 baseline file_hashes 中的 backend/frontend/scripts
    base_files = json.loads((DATA / "file_hashes.json").read_text(encoding="utf-8"))
    code_changed = []
    doc_changed = []
    for row in base_files["files"]:
        p = ROOT / row["path"]
        if not p.exists() or sha256(p) != row["sha256"]:
            if row["path"].startswith(("backend/", "frontend/", "scripts/")):
                code_changed.append(row["path"])
            else:
                doc_changed.append(row["path"])
    report["protection"]["code_changed"] = code_changed
    report["protection"]["doc_changed"] = doc_changed

    db_path = ROOT / "backend" / "eatwhat.db"
    base_db = json.loads((DATA / "db_baseline.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        rooms = con.execute("select count(*) from group_rooms").fetchone()[0]
        votes = con.execute("select count(*) from room_votes").fetchone()[0]
    finally:
        con.close()
    report["protection"]["db"] = {
        "sha256_before": base_db["file_sha256"],
        "sha256_now": sha256(db_path),
        "unchanged": sha256(db_path) == base_db["file_sha256"],
        "group_rooms": rooms,
        "room_votes": votes,
    }

    from backend.main import app
    admin = sorted({getattr(r, "path", "") for r in app.routes if "/admin" in getattr(r, "path", "")})
    report["protection"]["admin_routes"] = admin

    ok = (
        not report["live"]
        and not code_changed
        and report["protection"]["db"]["unchanged"]
        and rooms == 0 and votes == 0
        and not admin
    )
    report["protection"]["review_md_present"] = (PACK / "REVIEW.md").exists()
    report["protection"]["review_md_note"] = "Codex-created; this doc-sync run did not create or modify it."
    report["ok"] = ok
    (DATA / "doc_sync_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"ok={ok}",
        f"live_stale_files={list(report['live'])}",
        f"historical_r01_terms={hist}",
        f"code_changed={code_changed}",
        f"doc_changed={doc_changed}",
        f"db_unchanged={report['protection']['db']['unchanged']} group_rooms={rooms} room_votes={votes}",
        f"admin_routes={admin}",
    ]
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
