# 菜品图落地方案（已执行完毕，2026-10-24）

> 用途：把 100 道种子菜品（去重后 95 张图）接进卡面。
>
> **状态：已收口。** 95 张图由用户按小红书清单整包提供（`D:\谷歌\dish-images-all-95.zip`），
> 全部落进 `frontend/public/dishes/`，数据库 100 条菜品记录全部有 `image_url`，缺失 0。
> 实际执行与本文的差异见文末「§8 执行复盘」，图片台账以 `docs/DISH_IMAGES_LEDGER.md` 为准。

## 1. 口径（按你的要求逐条锁定）

| # | 项目 | 口径 |
|---|---|---|
| 1 | 字段 | `RecommendationItem` **只加** `image_url: Optional[str] = None` 一个字段，不动其他字段；取不到就是 `null`，前端遇 `null` 走无图占位，**不拿别的菜顶图** |
| 2 | 范围 | 只处理现有 100 道种子菜（`dishes_and_recipes` 表），不新增菜、不改菜名/菜系/价格 |
| 3 | 来源 | 只从 Wikimedia Commons / Unsplash / Pexels 取；其他站一律不进流程，除非先在此文补登出处再动 |
| 4 | 存放 | **落本地仓库**，见 §3；`image_url` 存**相对路径**（`/dishes/xxx.jpg`），禁止热链外站原图 |
| 5 | 台账 | 每张图一行：菜名 / 图片文件 / 来源页 / 授权类型 / 作者 / 下载日期 → `docs/DISH_IMAGES_LEDGER.md` |
| 6 | 缺失清单 | 三列：菜名 / 菜系 / 试过来源 → 与本方案同目录 `docs/DISH_IMAGES_MISSING.md` |

## 2. 后端改动（只有两处，先报备）

1. `backend/schemas.py` 的 `RecommendationItem` 增加 `image_url: Optional[str] = None`。
2. `backend/algorithms/single_recommender.py` 组装候选时带出 `image_url=dish.image_url or None`。
3. 种子脚本 `backend/scripts/init_seed_data.py`：把已下载文件的相对路径写进 `dishes_and_recipes.image_url`（该列已存在，**不需要迁移**）。
4. 群组推荐（批次 3）以后复用同一个字段，不另开。

不新增接口、不改 `/api/v1` 路径、不改前端既有字段解析。

## 3. 存放位置：`frontend/public/dishes/`

选它而不是后端静态目录，理由：

- Vite 的 `public/` 原样映射到站点根，`/dishes/x.jpg` 在 dev、build、Capacitor APK 三种形态下都能取到，不需要再配一条后端静态路由。
- 后端只负责"给路径"，不负责"给字节"，接口更薄；答辩演示换机器时不会因为后端没起静态服务而全盘无图。
- 图片属于展示素材，跟界面一起版本化，`git` 里能看到具体是哪张图进了仓库。

体积控制：统一 **800×450（16:9，与卡面图区比一致）**、JPEG q82、单张目标 ≤ 120 KB；95 张合计约 6–9 MB，可控。原始文件不留在仓库（只留处理后的成品）。

## 4. 文件命名

`frontend/public/dishes/<三位 dish_id>-<英文短名>.jpg`

- 同名菜（宫保鸡丁 / 麻婆豆腐 / 回锅肉 / 白灼虾 / 紫菜蛋花汤 各跨两种模式）**共用一张图**，文件名取较小的 dish_id，台账里写明覆盖的全部 dish_id。
- 因此 100 条记录 → **95 个文件**。

## 5. 检索与取图流程

1. 以 §6 表格的"主检索词"为主，先查 Commons（`action=query&generator=search&gsrnamespace=6`，文件命名空间）。
2. 命中则核对：是不是这道菜（不是同名异物）、授权是否为 CC0 / CC BY / CC BY-SA。
3. Commons 无合适图 → Unsplash → Pexels（关键词再补 "chinese food" 之类限定）。
4. 下载 → Pillow 居中裁 16:9 → 缩到 800×450 → 转 JPEG q82 → 落 `frontend/public/dishes/`。
5. 写台账一行 + `sha256`（便于论文附录取证）。
6. 三处都无合适图 → 不硬凑，写进缺失清单，`image_url` 留 `null`。

## 6. 待处理清单（95 张）

| # | 菜名 | 菜系 | dish_id | 拟用文件 `frontend/public/dishes/` | 主检索词 |
|---|---|---|---|---|---|
| 1 | 麻辣香锅 | 川湘菜 | 1 | `001-mala-xiang-guo-spicy-stir.jpg` | mala xiang guo spicy stir fry |
| 2 | 水煮肉片 | 川湘菜 | 2 | `002-sichuan-boiled-pork-slices.jpg` | sichuan boiled pork slices |
| 3 | 辣子鸡 | 川湘菜 | 3 | `003-chongqing-spicy-chicken.jpg` | chongqing spicy chicken |
| 4 | 干煸四季豆 | 川湘菜 | 4 | `004-dry-fried-green-beans.jpg` | dry fried green beans |
| 5 | 酸辣土豆丝 | 川湘菜 | 5 | `005-hot-and-sour-shredded-pota.jpg` | hot and sour shredded potato |
| 6 | 蜜汁叉烧饭 | 粤菜 | 6 | `006-char-siu-rice.jpg` | char siu rice |
| 7 | 白切鸡饭 | 粤菜 | 7 | `007-white-cut-chicken-rice.jpg` | white cut chicken rice |
| 8 | 烧鸭饭 | 粤菜 | 8 | `008-roast-duck-rice.jpg` | roast duck rice |
| 9 | 清炒菜心 | 粤菜 | 9 | `009-stir-fried-choy-sum.jpg` | stir fried choy sum |
| 10 | 例汤 | 粤菜 | 10 | `010-cantonese-soup.jpg` | cantonese soup |
| 11 | 红烧牛肉面 | 面食 | 11 | `011-braised-beef-noodle-soup.jpg` | braised beef noodle soup |
| 12 | 清汤牛肉面 | 面食 | 12 | `012-beef-noodle-soup-clear-bro.jpg` | beef noodle soup clear broth |
| 13 | 番茄鸡蛋面 | 面食 | 13 | `013-tomato-egg-noodle-soup.jpg` | tomato egg noodle soup |
| 14 | 牛肉粉丝汤 | 面食 | 14 | `014-beef-vermicelli-soup.jpg` | beef vermicelli soup |
| 15 | 麻辣烫套餐 | 麻辣烫 | 15 | `015-malatang.jpg` | malatang |
| 16 | 番茄麻辣烫 | 麻辣烫 | 16 | `016-tomato-malatang.jpg` | tomato malatang |
| 17 | 骨汤麻辣烫 | 麻辣烫 | 17 | `017-malatang-bone-broth.jpg` | malatang bone broth |
| 18 | 鸡胸肉沙拉 | 轻食 | 18 | `018-chicken-breast-salad.jpg` | chicken breast salad |
| 19 | 低脂鸡胸饭 | 轻食 | 19 | `019-grilled-chicken-rice-bowl.jpg` | grilled chicken rice bowl |
| 20 | 南瓜浓汤 | 轻食 | 20 | `020-pumpkin-soup.jpg` | pumpkin soup |
| 21 | 青椒肉丝 | 家常菜 | 21 | `021-shredded-pork-with-green-p.jpg` | shredded pork with green pepper |
| 22 | 鱼香肉丝 | 家常菜 | 22 | `022-yuxiang-shredded-pork.jpg` | yuxiang shredded pork |
| 23 | 宫保鸡丁 | 川湘菜 | 69,23 | `023-kung-pao-chicken.jpg` | kung pao chicken |
| 24 | 麻婆豆腐 | 川湘菜 | 65,24 | `024-mapo-tofu.jpg` | mapo tofu |
| 25 | 西红柿炒蛋 | 家常菜 | 25 | `025-tomato-scrambled-eggs.jpg` | tomato scrambled eggs |
| 26 | 紫菜蛋花汤 | 家常菜 | 82,26 | `026-seaweed-egg-drop-soup.jpg` | seaweed egg drop soup |
| 27 | 皮蛋瘦肉粥 | 粥粉面 | 27 | `027-century-egg-congee.jpg` | century egg congee |
| 28 | 肠粉 | 粥粉面 | 28 | `028-rice-noodle-roll.jpg` | rice noodle roll |
| 29 | 云吞面 | 粥粉面 | 29 | `029-wonton-noodles.jpg` | wonton noodles |
| 30 | 干炒牛河 | 粥粉面 | 30 | `030-beef-chow-fun.jpg` | beef chow fun |
| 31 | 石锅拌饭 | 韩餐 | 31 | `031-bibimbap.jpg` | bibimbap |
| 32 | 部队锅 | 韩餐 | 32 | `032-budae-jjigae-army-stew.jpg` | budae jjigae army stew |
| 33 | 兰州牛肉拉面 | 面食 | 33 | `033-lanzhou-beef-noodles.jpg` | lanzhou beef noodles |
| 34 | 牛肉炒面片 | 面食 | 34 | `034-fried-noodle-pieces-beef.jpg` | fried noodle pieces beef |
| 35 | 羊肉串 | 烧烤 | 35 | `035-lamb-skewers.jpg` | lamb skewers |
| 36 | 排骨莲藕汤 | 炖菜 | 36 | `036-lotus-root-pork-rib-soup.jpg` | lotus root pork rib soup |
| 37 | 砂锅豆腐 | 炖菜 | 37 | `037-claypot-tofu.jpg` | claypot tofu |
| 38 | 砂锅鸡 | 炖菜 | 38 | `038-claypot-chicken.jpg` | claypot chicken |
| 39 | 毛血旺 | 川湘菜 | 39 | `039-maoxuewang.jpg` | maoxuewang |
| 40 | 水煮鱼 | 川湘菜 | 40 | `040-sichuan-boiled-fish.jpg` | sichuan boiled fish |
| 41 | 回锅肉 | 川湘菜 | 70,41 | `041-twice-cooked-pork.jpg` | twice cooked pork |
| 42 | 凉拌折耳根 | 川湘菜 | 42 | `042-houttuynia-salad.jpg` | houttuynia salad |
| 43 | 虾饺皇 | 粤菜 | 43 | `043-har-gow-shrimp-dumpling.jpg` | har gow shrimp dumpling |
| 44 | 白灼虾 | 粤菜 | 72,44 | `044-boiled-shrimp.jpg` | boiled shrimp |
| 45 | 烧鹅拼饭 | 粤菜 | 45 | `045-roast-goose-rice.jpg` | roast goose rice |
| 46 | 老火靓汤 | 粤菜 | 46 | `046-cantonese-slow-soup.jpg` | cantonese slow soup |
| 47 | 招牌牛腩面 | 面食 | 47 | `047-beef-brisket-noodles.jpg` | beef brisket noodles |
| 48 | 酸菜牛肉面 | 面食 | 48 | `048-pickled-cabbage-beef-noodl.jpg` | pickled cabbage beef noodles |
| 49 | 藜麦鸡胸沙拉 | 轻食 | 49 | `049-quinoa-chicken-salad.jpg` | quinoa chicken salad |
| 50 | 三文鱼沙拉 | 轻食 | 50 | `050-salmon-salad.jpg` | salmon salad |
| 51 | 全麦鸡肉卷 | 轻食 | 51 | `051-whole-wheat-chicken-wrap.jpg` | whole wheat chicken wrap |
| 52 | 招牌麻辣烫 | 麻辣烫 | 52 | `052-malatang-bowl.jpg` | malatang bowl |
| 53 | 五花肉烤肉套餐 | 烤肉 | 53 | `053-korean-bbq-pork-belly.jpg` | korean bbq pork belly |
| 54 | 烤牛肉拼盘 | 烤肉 | 54 | `054-korean-bbq-beef-platter.jpg` | korean bbq beef platter |
| 55 | 烤蔬菜拼盘 | 烤肉 | 55 | `055-grilled-vegetables-platter.jpg` | grilled vegetables platter |
| 56 | 三文鱼刺身 | 日料 | 56 | `056-salmon-sashimi.jpg` | salmon sashimi |
| 57 | 鳗鱼饭 | 日料 | 57 | `057-unagi-rice.jpg` | unagi rice |
| 58 | 韩式炸鸡 | 韩餐 | 58 | `058-korean-fried-chicken.jpg` | korean fried chicken |
| 59 | 红烧狮子头 | 江浙菜 | 59 | `059-lion-head-meatball.jpg` | lion head meatball |
| 60 | 猪肚鸡汤 | 粥品 | 60 | `060-pork-tripe-chicken-soup.jpg` | pork tripe chicken soup |
| 61 | 番茄炒蛋 | 家常菜 | 61 | `061-tomato-scrambled-eggs.jpg` | tomato scrambled eggs |
| 62 | 青椒土豆丝 | 家常菜 | 62 | `062-shredded-potato-green-pepp.jpg` | shredded potato green pepper |
| 63 | 蒜蓉西兰花 | 家常菜 | 63 | `063-garlic-broccoli.jpg` | garlic broccoli |
| 64 | 手撕包菜 | 家常菜 | 64 | `064-hand-torn-cabbage.jpg` | hand torn cabbage |
| 65 | 鱼香茄子 | 川湘菜 | 66 | `066-yuxiang-eggplant.jpg` | yuxiang eggplant |
| 66 | 可乐鸡翅 | 家常菜 | 67 | `067-cola-chicken-wings.jpg` | cola chicken wings |
| 67 | 红烧排骨 | 家常菜 | 68 | `068-braised-pork-ribs.jpg` | braised pork ribs |
| 68 | 清蒸鲈鱼 | 家常菜 | 71 | `071-steamed-sea-bass.jpg` | steamed sea bass |
| 69 | 香菇滑鸡 | 家常菜 | 73 | `073-chicken-with-shiitake.jpg` | chicken with shiitake |
| 70 | 洋葱炒蛋 | 家常菜 | 74 | `074-onion-scrambled-eggs.jpg` | onion scrambled eggs |
| 71 | 韭菜炒鸡蛋 | 家常菜 | 75 | `075-chive-scrambled-eggs.jpg` | chive scrambled eggs |
| 72 | 酸辣白菜 | 家常菜 | 76 | `076-hot-and-sour-cabbage.jpg` | hot and sour cabbage |
| 73 | 干煸豆角 | 川湘菜 | 77 | `077-dry-fried-long-beans.jpg` | dry fried long beans |
| 74 | 蒜蓉生菜 | 家常菜 | 78 | `078-garlic-lettuce.jpg` | garlic lettuce |
| 75 | 西芹百合 | 家常菜 | 79 | `079-celery-with-lily-bulb.jpg` | celery with lily bulb |
| 76 | 冬瓜排骨汤 | 家常菜 | 80 | `080-winter-melon-pork-rib-soup.jpg` | winter melon pork rib soup |
| 77 | 番茄蛋汤 | 家常菜 | 81 | `081-tomato-egg-soup.jpg` | tomato egg soup |
| 78 | 玉米排骨汤 | 家常菜 | 83 | `083-corn-pork-rib-soup.jpg` | corn pork rib soup |
| 79 | 菌菇鸡汤 | 家常菜 | 84 | `084-mushroom-chicken-soup.jpg` | mushroom chicken soup |
| 80 | 电饭煲焖饭 | 家常菜 | 85 | `085-rice-cooker-rice.jpg` | rice cooker rice |
| 81 | 腊肠煲仔饭 | 粤菜 | 86 | `086-claypot-rice-chinese-sausa.jpg` | claypot rice chinese sausage |
| 82 | 电饭煲茶叶蛋 | 家常菜 | 87 | `087-tea-egg.jpg` | tea egg |
| 83 | 电饭煲红烧肉 | 家常菜 | 88 | `088-braised-pork-belly.jpg` | braised pork belly |
| 84 | 电饭煲青菜粥 | 家常菜 | 89 | `089-vegetable-congee.jpg` | vegetable congee |
| 85 | 空气炸锅鸡翅 | 家常菜 | 90 | `090-air-fryer-chicken-wings.jpg` | air fryer chicken wings |
| 86 | 空气炸锅薯条 | 家常菜 | 91 | `091-air-fryer-fries.jpg` | air fryer fries |
| 87 | 空气炸锅烤茄子 | 家常菜 | 92 | `092-air-fryer-eggplant.jpg` | air fryer eggplant |
| 88 | 空气炸锅三文鱼 | 家常菜 | 93 | `093-air-fryer-salmon.jpg` | air fryer salmon |
| 89 | 凉拌黄瓜 | 家常菜 | 94 | `094-smashed-cucumber-salad.jpg` | smashed cucumber salad |
| 90 | 凉拌木耳 | 家常菜 | 95 | `095-wood-ear-mushroom-salad.jpg` | wood ear mushroom salad |
| 91 | 凉拌豆腐丝 | 家常菜 | 96 | `096-tofu-skin-salad.jpg` | tofu skin salad |
| 92 | 凉拌鸡丝 | 家常菜 | 97 | `097-shredded-chicken-salad.jpg` | shredded chicken salad |
| 93 | 一锅出番茄牛腩 | 家常菜 | 98 | `098-tomato-beef-brisket-stew.jpg` | tomato beef brisket stew |
| 94 | 一锅出土豆炖鸡 | 家常菜 | 99 | `099-potato-chicken-stew.jpg` | potato chicken stew |
| 95 | 一锅出咖喱饭 | 家常菜 | 100 | `100-curry-rice.jpg` | curry rice |

## 7. 风险与论文相关事项

- **Commons 多为 CC BY-SA**：必须署名。计划在 App「我的 → 关于」里放一份图片来源页（批次 2 先落 `docs/DISH_IMAGES_LEDGER.md`，界面入口随 Profile 一起做），论文"数据来源"节直接引用台账。
- **Unsplash / Pexels**：各自许可允许免费商用、不强制署名，但台账照样记作者与页面，便于溯源。
- **不得用生成式占位图冒充真实菜品**：缺失就是缺失，走 `null` + 占位。
- 图片是"示意"，不承诺与该校食堂实际出品一致；论文表述写"菜品示意图，来源见附录"。

## 8. 执行分批

| 批次 | 范围 | 产出 |
|---|---|---|
| A | dish_id 1–20（外食·川湘/粤/面食前半） | 图 + 台账 + 首次缺失清单 |
| B | 21–40 | 图 + 台账 |
| C | 41–60 | 图 + 台账 |
| D | 61–80（下厨·家常菜） | 图 + 台账 |
| E | 81–100（电饭煲/空气炸锅/凉拌/一锅出） | 图 + 台账 + 汇总缺失清单 |

每批结束跑 `npm run build` 与卡面截图，双模式各一张，确认 `object-fit: cover` 下不糊、不变形。

## 8. 执行复盘（2026-10-24 收口）

| 项 | 计划 | 实际 |
|---|---|---|
| 来源 | Wikimedia Commons / Unsplash / Pexels | **小红书笔记实拍截图**（用户自选，逐张登记作者与笔记链接于 `docs/DISH_IMAGES_SOURCES_RAW.md`） |
| 规格 | 800×450 / JPEG q82 / ≤120KB | **672×890 竖版原图不裁切**，总量 17.0 MB（卡片端 `object-fit: cover` 取中间带） |
| 数量 | 95 张 | 95 张，0 缺失 |
| 命名 | `<三位id>-<slug>.jpg` | 一致（用户已按此命名，直接落盘） |
| 映射 | 菜名 → 路径（`gen_dish_image_map.py` 读本文清单表） | 改为 **按 id 匹配**（`scripts/build_dish_image_map.py`），避免「番茄炒蛋 / 西红柿炒蛋」这类近名菜错配 |
| 台账 | 逐张登记授权类型 | 改为逐张登记笔记标题 / 作者 / 链接（截图来源，无 CC 授权概念），见 `docs/DISH_IMAGES_LEDGER.md` |

两条偏离的理由：①竖版不裁切是为了不预判卡片比例——`object-fit: cover` 随时能改取景，而离线裁成 16:9 就不可逆；②按 id 匹配是因为文件名本身带 id，中文名匹配已经错过一次。

复现命令：

```powershell
python scripts/build_dish_image_map.py            # 按 id 重建 name -> /dishes/xxx.jpg
python scripts/render_image_ledger_from_sources.py # 重建台账与缺失清单
python -m backend.scripts.init_seed_data --force   # 把 image_url 写进数据库
```

