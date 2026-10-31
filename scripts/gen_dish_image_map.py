"""从 docs/DISH_IMAGES_PLAN.md 的清单表生成 backend/scripts/dish_images.py。

清单表每行含「菜名」与「拟用文件」，同名菜（跨模式）自然合并成一条。
用法：python scripts/gen_dish_image_map.py
"""
import re
from pathlib import Path

plan = Path("docs/DISH_IMAGES_PLAN.md").read_text(encoding="utf-8")
rows = []
for line in plan.splitlines():
    m = re.match(r"\|\s*\d+\s*\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|\s*`([^`]+)`\s*\|", line)
    if m:
        rows.append((m.group(1).strip(), m.group(2).strip()))

if len(rows) < 90:
    raise SystemExit(f"清单行数异常：{len(rows)}")

lines = [
    '"""菜名 → 示意图相对路径映射（自动生成，勿手改）。',
    "",
    "生成脚本：scripts/gen_dish_image_map.py",
    "图片来源与授权台账：docs/DISH_IMAGES_LEDGER.md",
    "缺失清单：docs/DISH_IMAGES_MISSING.md",
    "",
    "约定：同一道菜若跨\"外食/下厨\"两种模式（如宫保鸡丁），共用一张图，",
    "此表按菜名去重；文件实体在 frontend/public/dishes/ 下。",
    "查不到图或还没下载的菜不在表内 —— 调用方用 .get() 取，缺失即 None。",
    '"""',
    "",
    "DISH_IMAGE_PATHS = {",
]
missing = []
for name, fname in rows:
    if (Path("frontend/public/dishes") / fname).exists():
        lines.append(f'    "{name}": "/dishes/{fname}",')
    else:
        missing.append(name)
lines.append("}")
lines.append("")

Path("backend/scripts/dish_images.py").write_text("\n".join(lines), encoding="utf-8")
print("rows:", len(rows), "mapped:", len(rows) - len(missing), "missing:", len(missing))
