"""把 docs/_data/image_ledger.json 与 docs/_data/image_missing.json 渲染成给人看的 md。

用法：python scripts/render_image_docs.py
产物：
    docs/DISH_IMAGES_LEDGER.md   —— 来源与授权台账（论文数据来源节可直接引）
    docs/DISH_IMAGES_MISSING.md  —— 缺失清单（菜名 / 菜系 / 试过哪些来源）
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

LEDGER = Path("docs/_data/image_ledger.json")
MISSING = Path("docs/_data/image_missing.json")
OUT_LEDGER = Path("docs/DISH_IMAGES_LEDGER.md")
OUT_MISSING = Path("docs/DISH_IMAGES_MISSING.md")
PLAN = Path("docs/DISH_IMAGES_PLAN.md")
IMG_DIR = Path("frontend/public/dishes")


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def main() -> None:
    ledger = load(LEDGER)
    missing = load(MISSING)
    total_bytes = sum(e.get("bytes", 0) for e in ledger)
    licenses = Counter(e.get("license") or "未知" for e in ledger)
    have = {e["file"] for e in ledger if e.get("file")}
    on_disk = {p.name for p in IMG_DIR.glob("*.jpg")}
    orphan = sorted(on_disk - have)
    stale = sorted(have - on_disk)

    lines = [
        "# 菜品示意图·来源与授权台账",
        "",
        "> 自动生成，勿手改：`python scripts/render_image_docs.py`",
        "> 口径见 `docs/DISH_IMAGES_PLAN.md`；缺失清单见 `docs/DISH_IMAGES_MISSING.md`。",
        "",
        "## 汇总",
        "",
        f"- 成品图：**{len(ledger)}** 张，占 **{total_bytes / 1024 / 1024:.1f} MB**",
        f"- 授权分布：" + "、".join(f"{k} × {v}" for k, v in licenses.most_common()),
        f"- 缺失：**{len(missing)}** 道（见缺失清单）",
        f"- 规格：800×450 / JPEG q82 / progressive",
        "",
        "## 逐张台账",
        "",
        "| 菜名 | 菜系 | dish_id | 文件 | 来源页 | 授权 | 作者 | 源尺寸 | 字节 | sha256 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in sorted(ledger, key=lambda x: x.get("file", "")):
        page = e.get("source_page") or ""
        page_md = f"[Commons]({page})" if page else "—"
        author = (e.get("author") or "—").replace("|", "/")[:40]
        ids = ",".join(str(i) for i in e.get("dish_ids", []))
        width, height = (e.get("src_size") or [0, 0])[:2]
        lines.append(
            f'| {e.get("name", "")} | {e.get("cuisine", "")} | {ids} | `{e.get("file", "")}` | '
            f'{page_md} | {e.get("license") or "未知"} | {author} | {width}×{height} | '
            f'{e.get("bytes", 0) // 1024} KB | `{e.get("sha256", "")}` |'
        )

    if orphan or stale:
        lines += ["", "## 一致性检查", ""]
        if orphan:
            lines.append(f"- 磁盘上多出来的文件（台账没有）：{', '.join(orphan)}")
        if stale:
            lines.append(f"- 台账有但磁盘缺文件：{', '.join(stale)}")
    else:
        lines += ["", "一致性检查：台账与 `frontend/public/dishes/` 完全对齐。", ""]

    OUT_LEDGER.write_text("\n".join(lines) + "\n", encoding="utf-8")

    mlines = [
        "# 菜品示意图·缺失清单",
        "",
        "> 自动生成，勿手改：`python scripts/render_image_docs.py`",
        "> 这些菜在 Commons 上没有找到可用图，`image_url` 保持 `null`，前端显示无图占位；**没有拿别的菜的图顶替**。",
        "",
        f"共 **{len(missing)}** 道。",
        "",
        "| 菜名 | 菜系 | 拟用文件 | 试过的来源 / 查询 | 候选数 |",
        "|---|---|---|---|---|",
    ]
    for m in sorted(missing, key=lambda x: x.get("file", "")):
        tried = "；".join(m.get("tried") or []) or "—"
        mlines.append(
            f'| {m.get("name","")} | {m.get("cuisine","")} | `{m.get("file","")}` | {tried} | {m.get("candidates", 0)} |'
        )
    OUT_MISSING.write_text("\n".join(mlines) + "\n", encoding="utf-8")
    print(f"ledger {len(ledger)} imgs / {total_bytes/1024/1024:.1f} MB, missing {len(missing)}, orphan {len(orphan)}, stale {len(stale)}")


if __name__ == "__main__":
    main()
