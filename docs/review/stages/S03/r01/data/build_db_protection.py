"""生成 S03/r01 db_protection.json：受保护库指纹、隔离副本身份与 schema。"""

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path("D:/EatWhat")
OUT = ROOT / "docs" / "review" / "stages" / "S03" / "r01"
PROBE = OUT / "data" / "live_api_probe.json"

PATHS = {
    "demo": ROOT / "backend" / "eatwhat.db",
    "s10_import": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_source": ROOT / "backend" / "eatwhat_dev_pre00_r02.db",
    "iso": ROOT / "backend" / "eatwhat_s03_r01_iso.db",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in con.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' order by name"
            )
        ]
        return {table: con.execute(f"select count(*) from {table}").fetchone()[0] for table in tables}
    finally:
        con.close()


def schema_fingerprint(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select name, sql from sqlite_master where type='table' "
            "and name not like 'sqlite_%' order by name"
        ).fetchall()
        return hashlib.sha256(
            json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
    finally:
        con.close()


probe = json.loads(PROBE.read_text(encoding="utf-8"))

protected = {}
for name in ("demo", "s10_import", "dev_source"):
    path = PATHS[name]
    after = sha256(path)
    protected[name] = {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256_before": probe["protected_before"][name],
        "sha256_after": after,
        "rows": counts(path),
        "schema_fingerprint": schema_fingerprint(path),
        "unchanged": after == probe["protected_before"][name],
    }

iso = PATHS["iso"]
data = {
    "step": "S03",
    "round": "r01",
    "pytest_isolation": {
        "database_url_env": "<unset>",
        "engine": "sqlite:// (in-memory, StaticPool) from backend/tests/conftest.py",
        "note": (
            "专项与全量 pytest 只写内存库；真实 HTTP 探针只写 "
            "backend/eatwhat_s03_r01_iso.db（由开发源库复制）。"
            "未在演示库 / S10 库 / 开发源库上执行任何写探针。"
        ),
    },
    "protected": protected,
    "live_iso": {
        "path": iso.relative_to(ROOT).as_posix(),
        "source": "backend/eatwhat_dev_pre00_r02.db",
        "source_sha256": probe["protected_before"]["dev_source"],
        "sha256_initial": probe["iso_sha256_before"],
        "sha256_final": probe["iso_sha256_after"],
        "rows_before": probe["counts_before"],
        "rows_after": probe["counts_after"],
        "schema_fingerprint": schema_fingerprint(iso),
        "source_schema_fingerprint": schema_fingerprint(PATHS["dev_source"]),
        "expected_deltas": {
            "dishes_and_recipes": "+2（探针自建 2 道下厨菜）",
            "fridge_inventory": "+2（净增：user1 自带 3 条被清空后写入 4 条，user2 新增 1 条）",
            "eating_logs": "9→9",
            "group_rooms": "0→0",
            "room_votes": "0→0",
            "users": "4→4",
        },
        "probe_result": "docs/review/stages/S03/r01/data/live_api_probe.json",
        "probe_passed": probe["passed"],
        "probe_status_codes": probe["status_codes"],
        "probe_no_500": probe["no_500"],
    },
}

(OUT / "data" / "db_protection.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "protected_unchanged": {k: v["unchanged"] for k, v in protected.items()},
            "iso_schema_matches_source": data["live_iso"]["schema_fingerprint"]
            == data["live_iso"]["source_schema_fingerprint"],
            "probe_passed": data["live_iso"]["probe_passed"],
            "status_codes": data["live_iso"]["probe_status_codes"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
