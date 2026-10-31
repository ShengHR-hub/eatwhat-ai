"""生成 G1 源码 / 证据清单（最后生成，生成后不再修改包内文件）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[1]

SOURCE_FILES = [
    "frontend/src/components/SwipeCardDeck.vue",
    "frontend/src/views/mobile/Room.vue",
    "frontend/src/views/mobile/Home.vue",
    "frontend/vite.config.js",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/src/api/client.js",
    "frontend/src/api/index.js",
    "frontend/src/router/index.js",
    "frontend/src/layouts/MobileShell.vue",
    "frontend/src/components/AppTabBar.vue",
    "frontend/src/components/DishCard.vue",
    "frontend/src/components/LottieIcon.vue",
    "frontend/src/stores/persona.js",
    "frontend/src/stores/mode.js",
    "frontend/src/stores/algo.js",
    "frontend/src/utils/theme.js",
    "backend/main.py",
    "backend/routers/group_room.py",
    "backend/algorithms/group_recommender.py",
    "backend/algorithms/veto_rules.py",
    "backend/tests/test_s06_room_contract.py",
    "scripts/home-fit.mjs",
    "scripts/refill-fresh.mjs",
    "scripts/sandbox-sync.mjs",
    "scripts/check-colors.mjs",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry(path: Path, root: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    files = []
    for relative in SOURCE_FILES:
        path = ROOT / relative
        if path.exists():
            files.append(entry(path, ROOT))
        else:
            files.append({"path": relative, "missing": True})

    evidence = []
    for path in sorted(BASE.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SOURCE_MANIFEST.json":
            continue
        evidence.append(entry(path, ROOT))

    manifest = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "repo": str(ROOT),
        "branch": "master",
        "commits": 0,
        "commit_note": "仓库尚无 commit；版本以本清单固定",
        "source_files": files,
        "evidence_files": evidence,
        "counts": {
            "source_files": sum(1 for item in files if not item.get("missing")),
            "evidence_files": len(evidence),
        },
    }
    out = BASE / "SOURCE_MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    print("manifest sha256", sha256(out))


if __name__ == "__main__":
    main()
