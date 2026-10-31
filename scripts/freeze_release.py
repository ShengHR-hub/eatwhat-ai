"""S19 版本冻结器。

只有在统一验收 validation.json 明确 overall_ok=true 时才生成冻结清单。
本脚本不写业务代码/数据库；展示壳必须先看到冻结清单再启用。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/review/final/SOURCE_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files() -> list[Path]:
    result = []
    for folder in (ROOT / "backend", ROOT / "frontend/src", ROOT / "scripts"):
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".js", ".vue", ".json", ".css"}:
                result.append(path)
    for path in (
        ROOT / "frontend/package.json",
        ROOT / "frontend/package-lock.json",
        ROOT / "frontend/vite.config.js",
        ROOT / "frontend/capacitor.config.json",
        ROOT / "backend/eatwhat_g2_s10_full.db",
        ROOT / "backend/eatwhat_g3_bridge_iso.db",
        ROOT / "docs/review/consolidated/G3/data/parallel_benchmark_full.json",
    ):
        if path.exists():
            result.append(path)
    return sorted(set(result))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    if validation.get("overall_ok") is not True:
        raise SystemExit("统一验收未通过，拒绝冻结；展示壳不得启用")
    payload = {
        "frozen_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frozen": True,
        "validation": str(args.validation.resolve()),
        "files": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files()
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frozen": True, "manifest": str(OUT), "files": len(payload["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
