"""生成 S09/r03 送审包 manifest：r03 文件 + r02 84 项引用 + r04 PASS 原件。"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
R02 = ROOT / "docs/review/stages/S09/r02"
R03 = ROOT / "docs/review/stages/S09/r03"
R04_REPORT = ROOT / "docs/review/clearance-codex-r04-2026-10-24/REPORT.md"
R04_PASS = [
    ROOT / "docs/review/stages/PC01/r04/REVIEW.md",
    ROOT / "docs/review/stages/PC02/r02/REVIEW.md",
    ROOT / "docs/review/stages/PC03/r04/REVIEW.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def row(rel: str) -> dict:
    path = ROOT / rel
    return {
        "path": rel,
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() else None,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    r02_manifest_path = R02 / "SOURCE_MANIFEST.json"
    r02_manifest = json.loads(r02_manifest_path.read_text(encoding="utf-8"))
    paths = [item["path"] for item in r02_manifest["files"]]
    for path in sorted(R03.rglob("*")):
        if path.is_file() and path.name != "SOURCE_MANIFEST.json":
            paths.append(path.relative_to(ROOT).as_posix())
    for path in [R04_REPORT, *R04_PASS]:
        paths.append(path.relative_to(ROOT).as_posix())
    paths = sorted(set(paths))
    files = [row(rel) for rel in paths]
    payload = {
        "pack": "S09/r03",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "head": r02_manifest.get("head"),
        "head_note": r02_manifest.get("head_note"),
        "r02_manifest": {
            "path": "docs/review/stages/S09/r02/SOURCE_MANIFEST.json",
            "entry_count": len(r02_manifest["files"]),
            "sha256": sha256(r02_manifest_path),
        },
        "r04_pass_reports": {
            "total_report": row(R04_REPORT.relative_to(ROOT).as_posix()),
            "pc01": row(R04_PASS[0].relative_to(ROOT).as_posix()),
            "pc02": row(R04_PASS[1].relative_to(ROOT).as_posix()),
            "pc03": row(R04_PASS[2].relative_to(ROOT).as_posix()),
            "pc02_revision_note": "PC02 现行 PASS 为 PC02/r02；PC02/r01 REVIEW 为 FAIL 历史，未作为 PASS 附入。",
        },
        "files": files,
    }
    (R03 / "SOURCE_MANIFEST.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [item["path"] for item in files if not item["exists"] or sha256(ROOT / item["path"]) != item["sha256"]]
    print(json.dumps({"ok": not bad, "files": len(files), "bad": bad, "r02_entries": len(r02_manifest["files"])}, ensure_ascii=False, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
