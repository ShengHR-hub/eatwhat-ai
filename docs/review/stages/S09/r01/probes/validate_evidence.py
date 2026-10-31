"""S09 证据自校验：JSON 可解析、基线文件未变、演示库未写、evidence index 生成。

只读；不修改业务代码/数据库/台账。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"
LOGS = PACK / "logs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    checks = {}
    # 1) 所有 data/*.json 可解析
    bad_json = []
    for p in sorted(DATA.glob("*.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            bad_json.append({"path": p.name, "error": repr(exc)})
    checks["json_parse"] = {"ok": not bad_json, "bad": bad_json}

    # 2) 基线文件哈希不变
    base = json.loads((DATA / "file_hashes.json").read_text(encoding="utf-8"))
    changed = []
    for row in base["files"]:
        p = ROOT / row["path"]
        if not p.exists() or sha256(p) != row["sha256"]:
            changed.append(row["path"])
    checks["baseline_files_unchanged"] = {"ok": not changed, "changed": changed}

    # 3) 演示库文件哈希不变 + group_rooms/votes 仍为 0
    db_base = json.loads((DATA / "db_baseline.json").read_text(encoding="utf-8"))
    db_path = ROOT / "backend" / "eatwhat.db"
    db_now = sha256(db_path)
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        rooms = con.execute("select count(*) from group_rooms").fetchone()[0]
        votes = con.execute("select count(*) from room_votes").fetchone()[0]
        logs = con.execute("select count(*) from eating_logs").fetchone()[0]
        users = con.execute("select count(*) from users").fetchone()[0]
    finally:
        con.close()
    checks["demo_db_unchanged"] = {
        "ok": db_now == db_base["file_sha256"] and rooms == 0 and votes == 0,
        "sha256_before": db_base["file_sha256"],
        "sha256_now": db_now,
        "group_rooms": rooms,
        "room_votes": votes,
        "eating_logs": logs,
        "users": users,
    }

    # 4) 业务代码/SSOT/台账未被 S09 修改（对比基线哈希）
    checks["no_business_changes"] = {
        "ok": not changed,
        "note": "changed 列表同时覆盖业务代码、SSOT、台账与素材文档；空即未变。",
    }

    # 5) evidence index
    rows = []
    for p in sorted(PACK.rglob("*")):
        if p.is_file():
            rows.append(
                {
                    "path": str(p.relative_to(PACK)).replace("\\", "/"),
                    "bytes": p.stat().st_size,
                    "sha256": sha256(p),
                }
            )
    (DATA / "evidence_index.json").write_text(
        json.dumps({"files": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    checks["evidence_files"] = len(rows)

    ok = all(
        item.get("ok", True)
        for name, item in checks.items()
        if isinstance(item, dict)
    )
    payload = {"ok": ok, "checks": checks}
    (DATA / "validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
