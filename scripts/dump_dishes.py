"""一次性脚本：导出种子菜品清单（菜名 / 模式 / 菜系 / 价格 / 门店 / 图位），供图片台账核对。

用法（仓库根）：python scripts/dump_dishes.py
"""
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "backend" / "eatwhat.db"

con = sqlite3.connect(DB)
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("tables:", tables)

rows = con.execute(
    "select id, name, mode_type, cuisine_type, price, restaurant_id, appliance_tag, image_url "
    "from dishes order by mode_type, cuisine_type, id"
).fetchall()
print("count:", len(rows))
out = [
    {
        "id": r[0],
        "name": r[1],
        "mode_type": r[2],
        "cuisine_type": r[3],
        "price": r[4],
        "restaurant_id": r[5],
        "appliance_tag": r[6],
        "image_url": r[7],
    }
    for r in rows
]
Path("docs/_data/dishes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for o in out:
    print(o["id"], o["mode_type"], o["cuisine_type"], o["name"], o["appliance_tag"])
