"""生成「交给你来搜」的菜品图清单 docs/DISH_IMAGES_TODO.md。

读 DB + dish_images.py + frontend/public/dishes/ 现状，列出 95 张唯一图：
菜名 / 菜系 / 模式 / 建议文件名 / 搜索关键词 / 现状。
同名重复（宫保鸡丁 23/69 等）合并成一行，但 dish_id 列写全。
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_fetch_module():
    spec = importlib.util.spec_from_file_location("fetch", ROOT / "scripts" / "fetch_dish_images.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    fetch = load_fetch_module()
    conn = sqlite3.connect(ROOT / "backend" / "eatwhat.db")
    rows = conn.execute(
        "select id, name, mode_type, cuisine_type, image_url from dishes_and_recipes order by id"
    ).fetchall()

    grouped: dict[str, dict] = {}
    for dish_id, name, mode, cuisine, image_url in rows:
        fname = (image_url or "").split("/")[-1]
        item = grouped.setdefault(
            name,
            {"name": name, "cuisine": cuisine or "—", "modes": [], "ids": [], "file": ""},
        )
        item["ids"].append(dish_id)
        item["modes"].append("外食" if mode == "OUT_DINING" else "下厨")
        if not item["file"] and fname:
            item["file"] = fname

    have_dir = ROOT / "frontend" / "public" / "dishes"
    lines: list[str] = []
    existing = 0
    for index, item in enumerate(grouped.values(), start=1):
        exists = bool(item["file"]) and (have_dir / item["file"]).exists()
        existing += 1 if exists else 0
        keyword = " / ".join(fetch.ALIASES.get(item["name"], [])[:2]) or "—"
        modes = "/".join(sorted(set(item["modes"])))
        state = "已有" if exists else "**占位**"
        file_cell = f"`{item['file']}`" if item["file"] else "（待定）"
        ids = ",".join(str(x) for x in item["ids"])
        lines.append(
            f"| {index} | {item['name']} | {item['cuisine']} | {modes} | {file_cell} | {keyword} | {state} | {ids} |"
        )

    head = f"""# 菜品图清单（交给你来搜）

> 现状：100 条种子菜 → {len(grouped)} 张唯一图（5 组同名重复只算一张：宫保鸡丁 23/69、麻婆豆腐 24/65、回锅肉 41/70、白灼虾 44/72、紫菜蛋花汤 26/82）。
> 现有真图 **{existing}** 张先留着，其余走「菜品图位」占位；**你觉得哪张不行，按下面的文件名覆盖即可**。

## 怎么把图给我（二选一）

1. 按「建议文件名」命名，直接丢进 `D:\\EatWhat\\frontend\\public\\dishes\\`，同名覆盖；
2. 或者给我一个文件夹 / 压缩包（按菜名命名），我来批量改名 + 裁 800×450 + 补台账。

## 硬要求

- 只要**成品菜**实拍：不要食材、植株、菜谱书、菜单截图、店招、餐厅门脸；
- 授权干净：自己拍的 / CC0 / CC BY / CC BY-SA（记作者与出处）/ 明确可商用；
- 横图优先（16:9 最省事），最短边 ≥600px；给原图即可，裁切与压缩我来做。

表格里的「关键词」是给搜索用的英文词（`/` 分隔任选其一）。「现状」列标 **占位** 的是现在没有图的 13 道。

| # | 菜名 | 菜系 | 模式 | 建议文件名 | 搜索关键词 | 现状 | dish_id |
|---|---|---|---|---|---|---|---|
"""
    out = ROOT / "docs" / "DISH_IMAGES_TODO.md"
    out.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"rows {len(lines)} / existing {existing} / placeholders {len(lines) - existing} -> {out}")


if __name__ == "__main__":
    main()
