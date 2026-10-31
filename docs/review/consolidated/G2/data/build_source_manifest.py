"""生成 G2 源码 / 证据清单（最后生成）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[1]

SOURCE_FILES = [
    "backend/scripts/llm_batch_tagger.py",
    "backend/scripts/bridge_s10_runtime.py",
    "backend/scripts/fetch_amap_poi.py",
    "backend/scripts/import_open_recipes.py",
    "backend/scripts/migrate_s10_data_schema.py",
    "backend/scripts/verify_s10_import.py",
    "backend/scripts/s10_common.py",
    "backend/scripts/measure_recommend_sql.py",
    "backend/schemas.py",
    "backend/routers/recommend.py",
    "backend/algorithms/single_recommender.py",
    "backend/algorithms/group_recommender.py",
    "backend/models.py",
    "backend/config.py",
    "frontend/src/stores/algo.js",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry(path: Path, root: Path) -> dict:
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    sources = []
    for relative in SOURCE_FILES:
        path = ROOT / relative
        sources.append(entry(path, ROOT) if path.exists() else {"path": relative, "missing": True})
    evidence = []
    for path in sorted(BASE.rglob("*")):
        if not path.is_file() or path.name == "SOURCE_MANIFEST.json":
            continue
        evidence.append(entry(path, ROOT))
    manifest = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "repo": str(ROOT),
        "branch": "master",
        "commits": 0,
        "commit_note": "仓库尚无 commit；版本以本清单固定",
        "source_files": sources,
        "evidence_files": evidence,
        "counts": {
            "source_files": sum(1 for item in sources if not item.get("missing")),
            "evidence_files": len(evidence),
        },
    }
    out = BASE / "SOURCE_MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    print("manifest sha256", sha256(out))


if __name__ == "__main__":
    main()
