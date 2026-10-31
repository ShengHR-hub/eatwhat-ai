"""S06/r01：采集基线（日期、环境、git、受保护数据库状态）。只读。"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "baseline.json"

PROTECTED = (
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
    "backend/eatwhat_dev_pre00.db",
    "backend/eatwhat_s05_r01_iso.db",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def db_state(relative: str) -> dict:
    path = ROOT / relative
    payload: dict = {"path": relative, "exists": path.exists()}
    if not path.exists():
        return payload
    payload["sha256"] = sha256(path)
    payload["size"] = path.stat().st_size
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        payload["tables"] = sorted(tables)
        payload["columns"] = {
            table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            for table in ("restaurants", "dishes_and_recipes", "group_rooms", "room_votes")
            if table in tables
        }
        payload["counts"] = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "eating_logs",
                "group_rooms",
                "room_votes",
                "algo_configs",
            )
            if table in tables
        }
        if "room_votes" in tables:
            payload["room_vote_indexes"] = [
                row[1] for row in connection.execute("PRAGMA index_list(room_votes)")
            ]
        if "restaurants" in tables and "campus" in payload["columns"]["restaurants"]:
            payload["restaurant_campus"] = [
                list(row)
                for row in connection.execute(
                    "SELECT campus, COUNT(*) FROM restaurants GROUP BY campus ORDER BY campus"
                )
            ]
    finally:
        connection.close()
    return payload


def git(*args: str) -> dict:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return {
            "args": list(args),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:  # noqa: BLE001
        return {"args": list(args), "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    from backend.config import DATABASE_URL

    payload = {
        "captured_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "cwd": str(ROOT),
        "python": sys.version,
        "database_url_default": DATABASE_URL,
        "environment": {
            "node": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip(),
            "npm": subprocess.run(
                ["npm", "--version"], capture_output=True, text=True, shell=True
            ).stdout.strip(),
            "pytest": subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
        },
        "git": {
            "rev_parse": git("rev-parse", "HEAD"),
            "status_short": git("status", "--short"),
            "log": git("log", "--oneline", "-5"),
        },
        "databases": {relative: db_state(relative) for relative in PROTECTED},
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
