"""把清单表插进 docs/DISH_IMAGES_PLAN.md 的占位符（幂等：有表就替换）。"""
from pathlib import Path

plan = Path("docs/DISH_IMAGES_PLAN.md")
table = Path("docs/_data/dishes_table.md").read_text(encoding="utf-8").strip()
text = plan.read_text(encoding="utf-8")

start = text.find("## 6. 待处理清单")
end = text.find("## 7. 风险与论文相关事项")
if start == -1 or end == -1:
    raise SystemExit("占位区段没找到")

head = text[:start]
tail = text[end:]
new = head + "## 6. 待处理清单（95 张）\n\n" + table + "\n\n" + tail
plan.write_text(new, encoding="utf-8")
print("ok", len(new))
