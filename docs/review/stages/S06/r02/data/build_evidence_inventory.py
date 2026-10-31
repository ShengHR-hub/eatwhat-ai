"""生成 S06 证据清单（排除最后生成的 SOURCE_MANIFEST 与本清单自身）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PACKAGE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "evidence_inventory.json"
EXCLUDE = {
    "SOURCE_MANIFEST.json",
    "data/evidence_inventory.json",
    # 这两个日志由生成脚本的 stdout 重定向创建，属于自引用，不纳入清单。
    "logs/15_evidence_inventory.log",
    "logs/16_source_manifest.log",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    items = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(PACKAGE).as_posix()
        if relative in EXCLUDE or "__pycache__" in path.parts:
            continue
        items.append(
            {
                "path": relative,
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "package": "docs/review/stages/S06/r02",
        "note": "SOURCE_MANIFEST.json 最后生成，不在本清单内；本清单也不包含自身。",
        "count": len(items),
        "total_bytes": sum(item["size"] for item in items),
        "items": items,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"count": payload["count"], "total_bytes": payload["total_bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
