# 2026-10-24 整改复查与真实浏览器导航故障

## 本轮结论

用户报告的“点击底部足迹、我的无法进入”已在运行中的 `http://127.0.0.1:5173` 通过真实点击复现，完成一行修复后，相关导航恢复。原审查中的一部分修复已经生效，但 **F07、F08、F09 仍未修完整，不能整体标为关闭**。

本轮只修改 `frontend/src/components/AlgoSandboxDrawer.vue` 的错误卸载清理，没有改后端业务代码。后端写入复现全部在独立临时 SQLite 中进行；浏览器没有执行打卡、偏好保存、库存增删或建房。

## N01 / P1 — 首页离开时卸载异常，阻断底部导航（本轮已修）

### 真实复现

1. 打开 `/m/home`。
2. 点击底部“足迹”。
3. 地址和标题变为 `/m/footprint` / “足迹”，页面却保留首页内容，目标页未渲染。
4. 控制台出现：

```text
Unhandled error during execution of beforeUnmount hook
  at <AlgoSandboxDrawer>
ReferenceError: timer is not defined
```

证据：`navigation-before.json`、`navigation-before.jpg`。修复前的 DOM 断言为 `homeStillRendered=true`、`footprintRendered=false`、`pass=false`。

### 根因与修复

沙盒为修 F10 已把防抖计时迁到 Home，抽屉原有的 `timer` 声明和调度被删，但 `onBeforeUnmount` 中仍执行 `clearTimeout(timer)`。Home 一直挂载该抽屉，即使没有打开沙盒，离开首页也必然走这个卸载钩子；抛出的 ReferenceError 打断路由视图更新。

在 `frontend/src/components/AlgoSandboxDrawer.vue:46–48` 移除失效的 `clearTimeout(timer)`，保留恢复 `document.body.style.overflow` 的清理。没有通过禁用转场或吞异常掩盖问题。

### 修复后点击回归

在同一运行中的开发应用内使用真实浏览器点击，等待目标内容可见后再断言 URL 与页面一致：

| 点击路径 / 操作 | 结果 |
| --- | --- |
| 首页 → 足迹 | 出现“这周都吃了什么”、冷却看板与菜系分布 |
| 首页 → 我的 | 出现角色信息、饮食基因、忌口与战绩 |
| 我的 → 虚拟冰箱 | 出现“冰箱里有什么”与库存 |
| 我的 → 多人房间入口 | 出现“一起决定吃什么”及建房/输码入口 |
| 390×667，关闭沙盒后 → 足迹 | 进入目标页，body overflow 已恢复 |
| 390×667，足迹 → 我的 | 进入目标页 |
| 首页“换一个” | 麻婆豆腐切换到宫保鸡丁，随后仍可进入足迹 |

最终 **7 项点击检查通过，新产生的控制台 error 为 0**。期间第一次立即取样读到了正常的 `fade-leave-*` 转场中间态；随后改为等待目标内容可见，确认它不是第二个路由故障。原始观察与最终断言都保留在 `browser-results.json`，没有把中间态删掉伪装为一次成功。

![修复后真实点击进入足迹](footprint-after.jpg)

![修复后真实点击进入我的](profile-after.jpg)

两张截图均在页面根节点移除转场类且 opacity=1 后重新采集，并经图像复核；补拍过程控制台 error 为 0。

## 原审查相关项复核

### 已观察到生效的整改

- **F01 / F02：** 新增类别忌口和全否决回归在本轮后端测试中通过；本轮未以真实库构造全员否决房间。
- **F03 / F04 / F05 与 F11 的部分协议：** 已有截止、结算、完成后拒投、快照恢复等回归，本轮后端测试通过；浏览器本轮只检查房间入口，未重新进行两台终端完整投票与断线演示。
- **F06：** 390×667 与 390×844 两档真实 DOM 测量，页面不滚动，按钮不与底栏相交，两个按钮中心都命中自身。
- **F10 单人联动：** 将天气 β 调到 1，生效 β 归一化为 0.57；等待 AutoAnimate 离场节点和数字动效结束后，抽屉 Top5 与首页候选 Top5 的名字/分数完全一致，主卡为麻婆豆腐 87.6%。随后恢复默认参数。
- **F13：** 已有后端 `exclude_dish_ids` 回归通过；本轮浏览器验证单次换卡，没有重新连续划完 24 张验证完整换批。

两档首页实测：

| 视口 | 卡面高 | 操作行 bottom | 底栏 top | 重叠 | 按钮命中 |
| --- | ---: | ---: | ---: | ---: | --- |
| 390×667 | 261px | 607px | 615px | 0 | 两个均为自身 |
| 390×844 | 422px | 784px | 792px | 0 | 两个均为自身 |

### F07 / P2 — 路径型接口仍不遵守演示身份头

位置：`backend/routers/auth_user.py:113–129`，相关个人资料/红黑榜路径接口也仍应统一复核。

临时库实测：`X-User-Id:1` 调 PUT `/api/v1/users/2/preferences`，仍返回 200 并把 `recheck-only` 忌口写给角色 2。

对比：相同头部配 body user_id=2 的打卡现在保存到角色 1，说明 **body 优先级已经修正，path 一侧没有覆盖到**。规格要求演示身份头统一优先；这不是要求新增 JWT。

### F08 / P2 — 偏好更新仍允许越界向量与负预算入库

位置：`backend/schemas.py:49–53` 的 `PreferenceUpdate`；`backend/routers/auth_user.py:121–124`。

临时库实测：PUT 偏好 `{"base_vector":{"spicy_level":999},"default_budget":-100}` 返回 200，保存的向量仍为单一键且值 999，预算仍为 -100。

推荐请求/打卡金额的新增校验测试通过，不代表 `PreferenceUpdate` 也被校验。需要补齐这一路径的向量键集合、值域、有限值和预算约束，以及对应拒绝落库回归。

### F09 / P2 — 冰箱显示过期已修，购物清单和推荐仍使用过期库存

位置：`backend/routers/fridge.py:132–142`；`backend/algorithms/single_recommender.py:79–99`。

临时库录入创建于 30 天前、保质 3 天的鲜虾：GET 现在显示 `expire_days=0`，这部分修复生效；白灼虾购物清单仍把鲜虾列入 `owned_ingredients`，没有要求采购鲜虾。推荐的 `_fridge_status_score` 仍查询全部库存并使用原始 `expire_days`，没有统一时效过滤。

应将“当前可用库存”判断同时用于展示、推荐和采购，不能只改返回给页面的剩余天数。

### F10 群组参数链路仍需单独验收

单人沙盒写的是本次请求的 `override_params`，抽屉文案也明确“不改库里的 algo_configs”；房间结算改为读取数据库 `AlgoConfig`，只证明硬编码 0.5 已移除。两者不是同一参数传递链，本轮不将“沙盒 ω 实时影响多人房”标记通过。应按最终确认的参数作用域补足契约和演示。

### 其余范围

Room 真实划卡、扫码、素材与全量报告展示、主题出口剩余清理、扩容 N+1 和实验数据工程，没有在本轮重新全面验收。旧报告保留为审查时点记录，本报告只更新有新证据的项目。

## 验证输出

```text
python -m pytest -q
106 passed, 73 warnings in 6.24s

npm run build
✓ 775 modules transformed.
✓ built in 8.59s
```

退出码均为 0。警告包括 `datetime.utcnow()` 弃用、pytest 缓存权限及启动时 requests 依赖兼容提示；完整输出见 `backend-validation.log`、`frontend-validation.log`。没有声称这些警告已经修复。

浏览器最终证据见 `browser-results.json`；三项残留问题的临时库结果见 `backend-recheck.json`。临时库探针前后真实 `backend/eatwhat.db` SHA-256 一致：

```text
9ba340c3205f82cbdef3c497eb4f250be6d9a303a3413c179d838e707e4ccc7f
```

没有运行旧版、接口已过时的审查脚本，也没有在真实数据库上复现非法偏好或跨角色写入。
