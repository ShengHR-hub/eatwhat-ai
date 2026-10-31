"""Hash every evidence file in S05/r01 (except the manifest and this inventory)."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
PKG = ROOT / "docs/review/stages/S05/r01"
CST = timezone(timedelta(hours=8))
EXCLUDE = {"SOURCE_MANIFEST.json", "data/evidence_inventory.json"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kind(rel: str) -> str:
    if rel.startswith("browser/final/"):
        return "screenshot_final"
    if rel.startswith("browser/failure_shots/"):
        return "screenshot_failure"
    if rel.startswith("logs/"):
        return "log"
    if rel.startswith("data/"):
        return "data"
    if rel.endswith(".md"):
        return "document"
    if rel.endswith(".json"):
        return "json"
    return "other"


def main():
    files = []
    for p in sorted(PKG.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(PKG).as_posix()
        if rel in EXCLUDE:
            continue
        files.append({"path": rel, "sha256": sha(p), "size": p.stat().st_size, "kind": kind(rel)})
    summary = {}
    for f in files:
        summary[f["kind"]] = summary.get(f["kind"], 0) + 1
    payload = {
        "generated_at": datetime.now(CST).isoformat(),
        "package": "docs/review/stages/S05/r01",
        "excluded": sorted(EXCLUDE),
        "file_count": len(files),
        "kinds": summary,
        "files": files,
    }
    (PKG / "data/evidence_inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"file_count": len(files), "kinds": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
