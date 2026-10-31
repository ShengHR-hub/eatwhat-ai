"""生成 S06 受审源码清单（最后执行；执行后不再修改包内文件）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
PACKAGE = ROOT / "docs" / "review" / "stages" / "S06" / "r02"
OUT = PACKAGE / "SOURCE_MANIFEST.json"

S06_CHANGED = {
    "AGENTS.md",
    "MASTER_SPEC.md",
    "backend/algorithms/group_recommender.py",
    "backend/main.py",
    "backend/models.py",
    "backend/routers/group_room.py",
    "backend/schemas.py",
    "backend/scripts/migrate_s06_room_contract.py",
    "backend/tests/conftest.py",
    "backend/tests/test_identity_s01.py",
    "backend/tests/test_room.py",
    "backend/tests/test_s02_numeric_bounds.py",
    "backend/tests/test_s06_room_contract.py",
    "frontend/src/api/index.js",
    "frontend/src/stores/mode.js",
    "frontend/src/views/mobile/Room.vue",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect() -> list[Path]:
    files: list[Path] = []
    for relative in (
        "AGENTS.md",
        "MASTER_SPEC.md",
        "BATCH4_PLAN.md",
        "docs/REVIEW_RULES.md",
        "docs/review/STAGE_STATUS.md",
    ):
        path = ROOT / relative
        if path.exists():
            files.append(path)

    for path in (ROOT / "backend").rglob("*.py"):
        if "__pycache__" in path.parts or any(
            part.startswith(".codex") for part in path.parts
        ):
            continue
        files.append(path)

    frontend_root = ROOT / "frontend"
    for relative in (
        "package.json",
        "package-lock.json",
        "vite.config.js",
        "tailwind.config.js",
        "postcss.config.js",
        "index.html",
        "capacitor.config.json",
    ):
        path = frontend_root / relative
        if path.exists():
            files.append(path)
    for path in (frontend_root / "src").rglob("*"):
        if path.is_file() and path.suffix in {".js", ".vue", ".css"}:
            files.append(path)

    for path in (ROOT / "scripts").glob("*.mjs"):
        files.append(path)

    for path in (PACKAGE / "data").glob("*.py"):
        files.append(path)

    unique = {path.resolve(): path for path in files if path.is_file()}
    return [unique[key] for key in sorted(unique, key=lambda item: item.as_posix())]


def category(relative: str) -> str:
    if relative.startswith("backend/tests/"):
        return "backend_test"
    if relative.startswith("backend/"):
        return "backend"
    if relative.startswith("frontend/"):
        return "frontend"
    if relative.startswith("scripts/"):
        return "gate"
    if relative.startswith("docs/review/stages/S06/r02/data/"):
        return "evidence_tool"
    return "contract"


def main() -> None:
    items = []
    for path in collect():
        relative = path.relative_to(ROOT).as_posix()
        items.append(
            {
                "path": relative,
                "category": category(relative),
                "role": "s06_changed" if relative in S06_CHANGED else "context",
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "stage": "S06",
        "round": "r02",
        "ssot_version": "v2.3.6",
        "worktree": {
            "git_head": None,
            "note": "仓库无 commit；本清单以文件 SHA-256 固定受审版本。",
        },
        "count": len(items),
        "total_bytes": sum(item["size"] for item in items),
        "changed_count": sum(1 for item in items if item["role"] == "s06_changed"),
        "items": items,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "count": payload["count"],
                "changed_count": payload["changed_count"],
                "total_bytes": payload["total_bytes"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
