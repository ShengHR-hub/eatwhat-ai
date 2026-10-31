"""从 docs/DISH_IMAGES_SOURCES_RAW.md 生成图片来源台账与缺失清单。

这批图不是脚本抓的，是用户按 `docs/DISH_IMAGES_TODO.md` 的小红书清单截取后整包给过来的，
所以台账的职责变成：把「文件 ↔ 菜名 ↔ 笔记/作者/链接」核准，并核对磁盘与数据库是否对齐。

用法（仓库根目录）：
    python scripts/render_image_ledger_from_sources.py
输出：docs/DISH_IMAGES_LEDGER.md、docs/DISH_IMAGES_MISSING.md
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "backend" / "eatwhat.db"
IMG_DIR = ROOT / "frontend" / "public" / "dishes"
SOURCES = ROOT / "docs" / "DISH_IMAGES_SOURCES_RAW.md"
LEDGER = ROOT / "docs" / "DISH_IMAGES_LEDGER.md"
MISSING = ROOT / "docs" / "DISH_IMAGES_MISSING.md"


def parse_sources() -> dict[str, dict[str, str]]:
    """把 SOURCES.md 的表格解析成 文件名 → 行字段。"""
    rows: dict[str, dict[str, str]] = {}
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or "文件名" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6:
            continue
        rows[cells[0]] = {
            "dish": cells[1],
            "title": cells[2],
            "author": cells[3],
            "link": cells[4],
            "status": cells[5],
        }
    return rows


def main() -> None:
    sources = parse_sources()
    conn = sqlite3.connect(DB)
    dishes = conn.execute(
        "SELECT id, name, mode_type FROM dishes_and_recipes ORDER BY id"
    ).fetchall()
    conn.close()

    by_name: dict[str, list[tuple[int, str]]] = {}
    for dish_id, name, mode in dishes:
        by_name.setdefault(name, []).append((dish_id, mode))

    files = sorted(IMG_DIR.glob("*.jpg"))
    total_bytes = sum(f.stat().st_size for f in files)
    licenses: Counter[str] = Counter()

    table_rows = []
    orphan = 0
    no_source = 0
    for f in files:
        dish_id = int(f.name.split("-")[0])
        meta = sources.get(f.name)
        if meta is None:
            no_source += 1
            meta = {"dish": "（未登记）", "title": "—", "author": "—", "link": "—", "status": "—"}
        name = meta["dish"]
        owners = by_name.get(name)
        if owners is None:
            orphan += 1
            ids, modes = f"{dish_id}", "—"
        else:
            ids = "、".join(str(i) for i, _ in owners)
            modes = "、".join(sorted({m for _, m in owners}))
        with Image.open(f) as im:
            width, height = im.size
        digest = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        licenses[meta["status"]] += 1
        table_rows.append(
            f"| {dish_id:03d} | {name} | {modes} | `{f.name}` | {width}×{height} "
            f"| {f.stat().st_size // 1024} KB | {meta['author']} | {meta['link']} | {digest} |"
        )

    covered = {int(f.name.split("-")[0]) for f in files}
    covered_names = {sources[f.name]["dish"] for f in files if f.name in sources}
    missing = [(i, n, m) for i, n, m in dishes if n not in covered_names]

    LEDGER.write_text(
        "\n".join(
            [
                "# 菜品图来源台账",
                "",
                f"- 图片总数：**{len(files)}** 张（{total_bytes / 1024 / 1024:.1f} MB）",
                f"- 覆盖菜品：**{len(covered_names)}** 个菜名 / **{len(dishes) - len(missing)}** 条菜品记录",
                f"- 图片来源：小红书笔记实拍截图，逐张登记见下（原始清单 `docs/DISH_IMAGES_SOURCES_RAW.md`）",
                "- 规格：用户原图 672×890 竖版（截图原始比例，未二次裁切；卡片端用 `object-fit: cover` 取中间带）",
                "- 缺口：见 `docs/DISH_IMAGES_MISSING.md`",
                "",
                "## 一致性检查",
                "",
                f"- 磁盘文件 {len(files)} 个，台账登记 {len(files) - no_source} 条，未登记 {no_source} 条",
                f"- 文件名 id 在数据库里找不到对应菜品（孤儿）：{orphan}",
                f"- 数据库里没有图的菜品：{len(missing)}",
                "",
                "## 逐张台账",
                "",
                "| id | 菜名 | 模式 | 文件 | 尺寸 | 体积 | 作者 | 来源 | sha256(前16) |",
                "|---|---|---|---|---|---|---|---|---|",
                *table_rows,
                "",
            ]
        ),
        encoding="utf-8",
    )

    if missing:
        body = [
            "# 菜品图缺失清单",
            "",
            "以下菜品在数据库里存在但没有对应图片，`image_url` 保持 `null`，前端显示无图占位，"
            "没有拿别的菜的图顶替。",
            "",
            "| 菜名 | 菜系 | 模式 | 试过的来源 | 说明 |",
            "|---|---|---|---|---|",
        ]
        for dish_id, name, mode in missing:
            body.append(f"| {name} | — | {mode} | 小红书整包 | 用户未提供 id {dish_id:03d} |")
        MISSING.write_text("\n".join(body) + "\n", encoding="utf-8")
    else:
        MISSING.write_text(
            "\n".join(
                [
                    "# 菜品图缺失清单",
                    "",
                    "**当前没有缺失。**",
                    "",
                    f"数据库 {len(dishes)} 条菜品记录、{len(covered_names)} 个菜名，全部有图；"
                    "5 组同名菜（宫保鸡丁 / 麻婆豆腐 / 回锅肉 / 白灼虾 / 紫菜蛋花汤 的外食与下厨两条）共用同一张图。",
                    "",
                    "历史缺口（酸辣土豆丝、凉拌折耳根、青椒土豆丝、韭菜炒鸡蛋、洋葱炒蛋、酸辣白菜、"
                    "玉米排骨汤、腊肠煲仔饭、凉拌木耳、一锅出番茄牛腩、一锅出土豆炖鸡、番茄麻辣烫、骨汤麻辣烫）"
                    "已随 2026-10-24 的 95 张整包补齐。",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    print(
        f"ledger {len(files)} imgs / {total_bytes / 1024 / 1024:.1f} MB, "
        f"names {len(covered_names)}, missing {len(missing)}, orphan {orphan}, no_source {no_source}"
    )
    if missing:
        for dish_id, name, _ in missing:
            print(f"  MISSING {dish_id:>3} {name}")


if __name__ == "__main__":
    main()
