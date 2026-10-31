# 菜品图交办清单（已完成，2026-10-24 收口）

> 本文是交给用户搜图用的清单，**现已作废**：用户按此清单完成 95 张整包（`dish-images-all-95.zip`），
> 已全部落盘并通过校验（100 条菜品记录、95 个菜名、0 缺失）。
>
> 现状与台账见：
> - `docs/DISH_IMAGES_LEDGER.md` —— 逐张来源（笔记标题/作者/链接/尺寸/sha256）
> - `docs/DISH_IMAGES_MISSING.md` —— 当前无缺失
> - `docs/DISH_IMAGES_SOURCES_RAW.md` —— 用户提供的原始清单
>
> 若后续要换某道菜的图：把新图命名为 `<三位菜品 id>-<slug>.jpg` 放进 `frontend/public/dishes/`，
> 然后依次跑 `python scripts/build_dish_image_map.py`、`python scripts/render_image_ledger_from_sources.py`、
> `python -m backend.scripts.init_seed_data --force`。
