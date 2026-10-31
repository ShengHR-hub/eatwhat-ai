"""SQLite 在线备份：不锁写、不复制 WAL 半成品，保留最近 N 份。"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "eatwhat.db"
DEFAULT_DIR = ROOT / "backups"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f"数据库不存在：{args.db}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / f"{args.db.stem}_{datetime.now():%Y%m%d_%H%M%S}{args.db.suffix}"
    source = sqlite3.connect(args.db)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()
    backups = sorted(args.out_dir.glob(f"{args.db.stem}_*{args.db.suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[args.keep:]:
        old.unlink(missing_ok=True)
    print(f"backup={target} size={target.stat().st_size} kept={min(len(backups), args.keep)}")


if __name__ == "__main__":
    main()
