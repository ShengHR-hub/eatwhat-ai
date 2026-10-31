"""S05/r01 baseline capture (read-only).

Writes:
  data/baseline.json          environment, worktree, DB identity, hashes
  logs/00_baseline.log        human-readable copy

Never writes to backend/eatwhat.db, backend/eatwhat_batch4.db or
backend/eatwhat_dev_pre00_r02.db.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
OUT = ROOT / "docs/review/stages/S05/r01"
CST = timezone(timedelta(hours=8))

PROTECTED = [
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
]

SOURCE_DIRS = [
    "backend",
    "frontend/src",
    "frontend/public",
    "scripts",
    "docs/review",
]
SOURCE_FILES = [
    "AGENTS.md",
    "MASTER_SPEC.md",
    "MOBILE_VISUAL_SPEC.md",
    "WEATHERPILL_GLASS.md",
    "DASHBOARD_EXPANSION.md",
    "BATCH4_PLAN.md",
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/vite.config.js",
    "frontend/tailwind.config.js",
    "frontend/index.html",
]
SKIP_PARTS = {
    "__pycache__",
    "node_modules",
    ".git",
    "dist",
    ".pytest_cache",
    "dishes",
    "lottie",
}
SKIP_PREFIXES = (
    "docs/review/stages/",
    "docs/review/clearance-",
    "docs/review/simulation/",
    "docs/review/audit-",
    "docs/review/recheck-",
    "docs/_data/",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> dict:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {"args": list(args), "exit": proc.returncode, "out": proc.stdout, "err": proc.stderr}


def collect_sources() -> list[dict]:
    files: list[dict] = []
    for rel in SOURCE_FILES:
        p = ROOT / rel
        if p.is_file():
            files.append({"path": rel, "sha256": sha256(p), "size": p.stat().st_size})
    for rel_dir in SOURCE_DIRS:
        base = ROOT / rel_dir
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS]
            for name in filenames:
                p = Path(dirpath) / name
                rel = p.relative_to(ROOT).as_posix()
                if any(rel.startswith(pref) for pref in SKIP_PREFIXES):
                    continue
                if p.suffix.lower() in {".pyc", ".log", ".map"}:
                    continue
                files.append({"path": rel, "sha256": sha256(p), "size": p.stat().st_size})
    seen = {}
    for item in files:
        seen[item["path"]] = item
    return [seen[k] for k in sorted(seen)]


def sqlite_identity(rel: str) -> dict:
    import sqlite3

    p = ROOT / rel
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            r[0]
            for r in con.execute(
                "select name from sqlite_master where type='table' order by name"
            )
        ]
        counts = {}
        for t in (
            "users",
            "restaurants",
            "dishes_and_recipes",
            "user_preferences",
            "fridge_inventory",
            "eating_logs",
            "group_rooms",
            "room_votes",
            "algo_configs",
        ):
            if t in tables:
                counts[t] = con.execute(f"select count(*) from {t}").fetchone()[0]
        dish_cols = [
            r[1] for r in con.execute("PRAGMA table_info(dishes_and_recipes)")
        ]
        restaurant_cols = [
            r[1] for r in con.execute("PRAGMA table_info(restaurants)")
        ]
    finally:
        con.close()
    return {
        "path": rel,
        "sha256": sha256(p),
        "size": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(),
        "counts": counts,
        "dishes_columns": dish_cols,
        "restaurants_columns": restaurant_cols,
    }


def main() -> int:
    captured = datetime.now(CST).isoformat()
    status = git("status", "--short")
    status_lines = [
        line
        for line in status["out"].splitlines()
        if line.strip() and not line.startswith("?? .pytest")
    ]
    staged = git("diff", "--cached", "--stat")
    unstaged = git("diff", "--stat")

    def diff_hash(args: list[str]) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
        )
        return hashlib.sha256(proc.stdout).hexdigest()

    files = collect_sources()
    netstat = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, errors="replace"
    ).stdout.splitlines()
    listening = [
        line
        for line in netstat
        if any(f":{port} " in line for port in (8000, 5173, 9222))
        and "LISTENING" in line
    ]
    data = {
        "captured_at": captured,
        "workspace": str(ROOT),
        "git": {
            "branch": git("branch", "--show-current")["out"].strip(),
            "head_exit": git("rev-parse", "HEAD")["exit"],
            "commit_count": git("rev-list", "--count", "--all")["out"].strip(),
            "status_total": len(status_lines),
            "status_head": status_lines[:60],
            "staged_diff_sha256": diff_hash(["diff", "--cached", "--binary"]),
            "unstaged_diff_sha256": diff_hash(["diff", "--binary"]),
        },
        "env": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "node": subprocess.run(
                ["node", "-v"], capture_output=True, text=True
            ).stdout.strip(),
            "npm": subprocess.run(
                ["npm", "-v"], capture_output=True, text=True, shell=True
            ).stdout.strip(),
        },
        "protected_databases": [sqlite_identity(rel) for rel in PROTECTED],
        "source_files": files,
        "source_file_count": len(files),
        "listening_ports": listening,
    }

    (OUT / "data/baseline.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"captured_at={captured}",
        f"branch={data['git']['branch']} head_exit={data['git']['head_exit']} commits={data['git']['commit_count']}",
        f"status_total={data['git']['status_total']}",
        f"staged_diff_sha256={data['git']['staged_diff_sha256']}",
        f"unstaged_diff_sha256={data['git']['unstaged_diff_sha256']}",
        f"env={data['env']}",
        f"source_files={len(files)}",
        "",
    ]
    for db in data["protected_databases"]:
        lines.append(
            f"DB {db['path']} sha256={db['sha256']} size={db['size']} counts={db['counts']}"
        )
        lines.append(
            f"   dishes_columns_has_allergen_tags={'allergen_tags' in db['dishes_columns']} "
            f"dishes_columns_has_deleted_at={'deleted_at' in db['dishes_columns']} "
            f"restaurants_columns_has_campus={'campus' in db['restaurants_columns']}"
        )
    lines.append("")
    lines.append("listening ports 8000/5173/9222:")
    lines.extend(data["listening_ports"] or ["  (none)"])
    (OUT / "logs/00_baseline.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
