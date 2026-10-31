# S02/r01 独立复审报告

审查时间：2026-10-26（Asia/Shanghai）  
审查方：Codex  
受审包：`docs/review/stages/S02/r01/`  
受审 manifest：145 项，fingerprint `eb17fe30bea0b2c3e530da3465006504944af480f88d65ba4724ce0e17f9b03f`

## 最终结论

**S02/r01：FAIL。**

专项 47 条与后端全量测试均为绿色，manifest 逐文件 0 失配，但方案 A 的历史脏向量守卫没有覆盖所有偏好写入路径，存在可复现的契约违背和持久化不一致。S02 不得放行，台账保持 `S02=READY`、`S03=LOCKED`。

## 独立核验

| 条目 | 结果 |
| --- | --- |
| manifest | 145/145 存在且 SHA 全部匹配 |
| 专项测试 | `47 passed` |
| 后端全量 | `257 passed, 1 skipped`；skip 为既有 Windows 符号链接权限用例 |
| 代码入口 | 直接检查 `PreferenceUpdate`、`update_preferences`、数值校验和异常处理 |
| 隔离 HTTP/数据库 | 使用内存库和提交包隔离探针；未写演示库、S10 库或开发源库 |
| 受保护库 | `eatwhat.db`、`eatwhat_batch4.db`、`eatwhat_dev_pre00_r02.db` SHA 保持不变 |

## 阻断问题

### S02-R01-01（P2）：历史非法向量可通过非向量偏好更新继续持久化

源码位置：[backend/routers/auth_user.py](D:/EatWhat/backend/routers/auth_user.py:133-160)。历史值校验位于 `if payload.base_vector is not None:` 分支内；只提交 `default_budget`、`veto_tags` 或 `preferred_cuisines` 时不会执行 `_valid_stored_value` 检查，随后直接 `db.commit()`。

独立复现（内存 SQLite）：

1. 将用户 1 的历史向量设置为 `{"spicy_level":95,"oily_level":0.8}`。
2. `PUT /api/v1/users/1/preferences`，body `{"default_budget":31}`，header `X-User-Id: 1`。
3. 实际响应为 **200**；预算写入 31；非法历史向量仍为两键且含 95。

这违反已确认方案 A 的“旧值若存在非法值或未知键，应原子拒绝，不能静默修复/保留坏值”以及 S02 的“入库后的口味向量始终八键完整、有限、值域正确”。

### S02-R01-02（P2）：历史未知键在向量更新中被静默丢弃

同一位置构造 `completed = {key: merged.get(key, DEFAULT_FEATURE_VECTOR[key]) for key in GENE_KEYS}`，只遍历合法八键，没有先检查 `prefs.base_vector` 的键集合。若历史向量含 `umami_level` 等未知键，提交任意合法 `base_vector` 会返回 200 并把未知键静默删除，而不是按用户确认的历史非法/未知值守卫返回 409、保持数据库不变。

## 下一轮验收要求

1. 在所有 `PUT /users/{id}/preferences` 请求路径中，先对历史向量做统一守卫：键集合必须等于或可补齐为八键；历史未知键、非数字、布尔、NaN/Infinity、越界值统一返回 409，且任何预算/忌口/菜系字段都不得提交。
2. 对合法但缺键的历史向量按方案 A 补齐缺失键为 0.5；补齐只能发生在历史值全部合法且无未知键时。
3. 增加独立回归：仅改预算、仅改忌口、仅改菜系、同时改合法向量；分别覆盖历史缺键、历史未知键、历史越界、历史非有限值，断言状态码和数据库前后快照。
4. 重新生成 S02/r02 的 manifest、完整日志和隔离 HTTP 证据；提交后停手等待复审。不得修改台账或开始 S03。

## 放行状态

本报告不签 PASS，不更新台账。S02 仍为当前整改步骤；S03 及后续步骤继续锁定。

