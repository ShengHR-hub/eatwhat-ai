"""按「菜品 id」重建 菜名 → 图片路径 映射（backend/scripts/dish_images.py）。

为什么不再按菜名匹配：图文件名由用户按 `<三位id>-<slug>.jpg` 命名，
id 是唯一可靠的锚点；按中文名匹配过一次「番茄炒蛋 / 西红柿炒蛋」这种近名菜就会错。

用法（仓库根目录）：
    python scripts/build_dish_image_map.py
输出：rows / mapped / missing 三个数字，写回 backend/scripts/dish_images.py。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "backend" / "eatwhat.db"
IMG_DIR = ROOT / "frontend" / "public" / "dishes"
TARGET = ROOT / "backend" / "scripts" / "dish_images.py"

NAME_RE = re.compile(r"^(\d{3})-.*\.(jpe?g|png|webp)$", re.IGNORECASE)

HEADER = '''"""菜名 → 示意图相对路径映射（自动生成，勿手改）。

生成脚本：scripts/build_dish_image_map.py
图片来源台账：docs/DISH_IMAGES_LEDGER.md
缺失清单：docs/DISH_IMAGES_MISSING.md

约定：文件名以 <三位菜品 id> 开头（如 024-mapo-tofu.jpg），按 id 关联，
同一道菜跨「外食/下厨」两种模式时共用一张图，此表按菜名去重；
文件实体在 frontend/public/dishes/ 下。
查不到图的菜不在表内 —— 调用方用 .get() 取，缺失即 None。
"""

DISH_IMAGE_PATHS = {
'''


def main() -> None:
    files: dict[int, str] = {}
    for path in sorted(IMG_DIR.iterdir()):
        m = NAME_RE.match(path.name)
        if m:
            files[int(m.group(1))] = path.name

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, name FROM dishes_and_recipes ORDER BY id"
    ).fetchall()
    conn.close()

    entries: dict[str, str] = {}
    shared: list[tuple[int, str]] = []  # 同名菜的下厨副本：没有独立文件，共用同名图
    missing: list[tuple[int, str]] = []
    for dish_id, name in rows:
        filename = files.get(dish_id)
        if filename is None:
            if name in entries:
                shared.append((dish_id, name))
            else:
                missing.append((dish_id, name))
            continue
        entries.setdefault(name, f"/dishes/{filename}")

    body = "".join(
        f'    "{name}": "{url}",\n' for name, url in sorted(entries.items())
    )
    TARGET.write_text(HEADER + body + "}\n", encoding="utf-8")

    print(
        f"rows: {len(rows)}  names: {len(entries)}  "
        f"shared: {len(shared)}  missing: {len(missing)}"
    )
    if shared:
        print("  shared(同名菜共图): " + ", ".join(str(i) for i, _ in shared))
    if missing:
        for dish_id, name in missing:
            print(f"  MISSING {dish_id:>3} {name}")


if __name__ == "__main__":
    main()
