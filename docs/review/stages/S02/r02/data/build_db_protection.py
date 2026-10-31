"""重新生成 db_protection.json：受保护库哈希、隔离副本身份、探针前后行数。"""

import hashlib
import json
import sqlite3

ROOT = "D:/EatWhat"


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


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
        return {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in tables}
    finally:
        con.close()


def schema(path):
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


OUT = "docs/review/stages/S02/r02"
probe = json.load(open(f"{OUT}/data/live_api_probe.json", encoding="utf-8"))
demo = "backend/eatwhat.db"
batch = "backend/eatwhat_batch4.db"
dev = "backend/eatwhat_dev_pre00_r02.db"
iso = "backend/eatwhat_s02_r02_iso.db"

PROTECTED_BEFORE = {
    "demo": "775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b",
    "s10_import": "315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28",
    "dev_source": "b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579",
}

protected = {}
for name, path in (
    ("demo", demo),
    ("s10_import", batch),
    ("dev_source", dev),
):
    after = sha(path)
    protected[name] = {
        "path": path,
        "sha256_before": PROTECTED_BEFORE[name],
        "sha256_after": after,
        "rows": counts(path),
        "unchanged": after == PROTECTED_BEFORE[name],
    }

data = {
    "step": "S02",
    "round": "r02",
    "pytest_isolation": {
        "database_url_env": "<unset>",
        "engine": "sqlite:// (in-memory, StaticPool) from backend/tests/conftest.py",
        "note": (
            "REST 用例通过 dependency_overrides[get_db] 注入内存库；"
            "test_room 的 room_env 夹具 monkeypatch group_room.SessionLocal。"
            "未在演示库/S10 库/开发源库上执行写探针。"
        ),
    },
    "protected": protected,
    "live_iso": {
        "path": iso,
        "source": dev,
        "source_sha256": PROTECTED_BEFORE["dev_source"],
        "sha256_initial": probe["iso_sha256_before"],
        "sha256_final": sha(iso),
        "schema_fingerprint": schema(iso),
        "source_schema_fingerprint": schema(dev),
        "rows_before": probe["counts_before"],
        "rows_after": probe["counts_after"],
        "expected_deltas": {
            "eating_logs": "+1（唯一合法打卡 cost_amount=0）",
            "user_preferences": "4 行不变；user1 向量按方案 A 部分合并；user2 历史向量用例后已还原",
            "group_rooms": "0→0",
            "room_votes": "0→0",
            "fridge_inventory": "12→12",
        },
        "probe_result": f"{OUT}/data/live_api_probe.json",
        "probe_passed": probe["passed"],
    },
}

with open(f"{OUT}/data/db_protection.json", "w", encoding="utf-8") as handle:
    json.dump(data, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

print(
    json.dumps(
        {
            "protected_unchanged": {
                key: value["unchanged"] for key, value in protected.items()
            },
            "iso_schema_matches_source": data["live_iso"]["schema_fingerprint"]
            == data["live_iso"]["source_schema_fingerprint"],
            "iso_rows": [data["live_iso"]["rows_before"], data["live_iso"]["rows_after"]],
            "probe_passed": data["live_iso"]["probe_passed"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
