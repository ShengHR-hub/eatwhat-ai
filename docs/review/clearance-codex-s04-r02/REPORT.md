# S04/r02 独立复审报告

审查时间：2026-10-26 23:44（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S04/r02/SOURCE_MANIFEST.json`，152 项；fingerprint `f23f227014d275dc51171305fa7f635268a6d7d4ba1150f37c754378ba306350`。  
审查范围：S04 的 F01、F02、N04、回归与证据身份；S05 不在本次开放范围。

## 验收结果

| 条目 | 独立检查 | 结果 | 判定 |
| --- | --- | --- | --- |
| 版本与证据清单 | 复算 manifest 中 152 项 SHA；按清单生成规则独立枚举文件范围 | 152/152 匹配；缺失 0、额外 0、重复 0；fingerprint 一致 | PASS（台账更新前） |
| F01 已登记具体/类别标签 | 检查共享匹配器、r02 测试及隔离 HTTP 探针 | `鲜虾` 只排虾类，单人与群组集合一致；`海鲜` 保留 3、排除 7；已测正反例通过 | PASS（仅已登记标签） |
| F01 未知标签精确匹配 | 对生产 `hits()` 直接执行未知词包含反例，并对照 D-S04-02 | 未知标签仍作子串匹配，违反“只精确匹配”；决策 JSON 的 `unknown` 口径也自相矛盾 | **FAIL，P2** |
| F02 存活候选同分 | 核对固定样本独立期望与 observed，并运行全套回归 | `survivor_tie` 两候选均为 52.8，稳定选 dish 3；固定样本 35/6/5/7 组均匹配 | PASS |
| N04 NULL 向量 | 检查单人/群组消费点及隔离 API 探针 | NULL 菜未进入单人推荐或群组 shortlist；仅 NULL 候选时 API 200、空列表、`combo=null` | PASS |
| 受保护数据库 | 复算当前演示库、S10 库、开发源库 SHA-256 | 三库与提交基线相同，见下文 | PASS |
| r01 历史证据保全 | 对照 r02 `CHECKS.md` §6 的事故披露 | r01 多个 data/log 文件被重写，无法恢复原始字节；虽已披露，仍不符合保留旧轮原件要求 | **FAIL，P2 流程/证据完整性** |
| 后端回归 | Codex 重新运行 S04 定向与后端全量测试 | 定向 73 passed；全量 363 passed、1 skipped、61 warnings | PASS（测试结果） |

## 阻断问题

### S04-F01-UNK-01：未知忌口文本没有按精确匹配处理

D-S04-02 明确规定未知文本只精确匹配。`expand_tags()` 对未知文本原样保留，但 `_token_matches()` 对所有多字 token 共用包含匹配，未区分注册过的类别/同义词别名与未知输入。因此未知标签仍能误过滤含该子串的食材。

Codex 使用 Unicode 转义在生产函数上复现：

```text
标签「秋葵」不是类别或已登记同义词；候选「秋葵炒蛋」 => matched=True（期望 False）
标签「核桃」不是类别或已登记同义词；候选「核桃仁」 => matched=True（期望 False）
精确候选「秋葵」 + 标签「秋葵」 => matched=True（期望 True）
```

源码位置：`backend/algorithms/veto_rules.py:204-217`。当前测试只断言未知标签全等命中和完全无关词不命中，未覆盖“候选包含未知标签但不全等”的反例：`backend/tests/test_s04_algorithms.py:243-245`。决策记录 `data/decision_f01.json` 的 statement 要求“只精确匹配”，但 semantics.unknown 写成“精确/包含匹配”，两者冲突。

**下一轮验收要求**：

- 让匹配器保留 token 来源/类型；只有类别展开出的成员与明确登记的具体同义词组可以做包含匹配，未知输入必须规范化后全等。
- 增加未知词全等正例，以及候选前缀/后缀包含未知词的负例；保留 `鲜虾` 同义词包含匹配、类别展开、单人与群组一致性及鱼香肉丝/豆腐/党参反例。
- 修正决策 JSON 中 `semantics.unknown` 与 statement 的矛盾；不改变用户已确认的语义。
- 用隔离 API/群组 shortlist 补测未知标签，并重跑 S04 定向与后端全量回归。

### S04-EVID-01：r01 包内证据被重写

r02 `CHECKS.md` §6 披露：r02 输出路径曾误指向 r01，导致 r01 的 `data/fixed_samples.json`、`data/live_api_probe.json`、`data/db_protection.json`、`validation.json` 与 `logs/20_live_server.log` 被重写。r01 的 REVIEW、报告、manifest 和主要说明文件未变，但受影响证据的原始字节无法恢复。r02 自身证据已单独复核，事故也有如实披露；这不改变本轮功能反例，却意味着不能再声称 r01 整包“原样保留”。

**处理要求**：不再写入 r01 或已提交的 r02。后续包应将当前 r01 受影响文件标记为重建件并固定其现状哈希，明确原始字节不可恢复；在 S04 最终 PASS 前，需由用户明确接受这一历史证据例外，或提供可验证的原始备份。不得把语义等价表述成字节原件恢复。

## 回归与隔离数据

- S04 定向命令：`python -m pytest tests/test_s04_algorithms.py tests/test_veto_and_consensus.py tests/test_time_decay.py tests/test_single_recommender.py tests/test_group_recommender.py tests/test_combo_optimizer.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-codex-20261026-s04-r02-target`，cwd `D:\EatWhat\backend`，exit 0，**73 passed**。
- 后端全量：`python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-codex-20261026-s04-r02-review`，cwd `D:\EatWhat\backend`，exit 0，**363 passed, 1 skipped, 61 warnings**。skip 是既有 Windows 符号链接权限场景；warnings 为既有 `datetime.utcnow()` 弃用，另有 requests/urllib3 依赖版本提示。
- 首次按默认临时目录运行全量测试时，327 passed、37 errors；失败均为 pytest `tmp_path` 创建时对用户临时目录 `WinError 5`。显式指定仓库内全新隔离 basetemp 后全量测试通过，因此不作为代码失败。
- 独立复算固定样本：忌口 35、衰减 6、群组 5、套餐 7，`all_match=true`；`survivor_tie` observed/expected 均为 52.8。
- 已提交的真实隔离 HTTP 探针摘要复核通过：具体标签 8 保留/2 排除，类别标签 3 保留/7 排除；单人与 shortlist 集合一致；NULL 菜未返回。该探针没有覆盖未知标签包含反例。
- 当前受保护数据库 SHA-256：演示库 `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b`；S10 库 `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`；开发源库 `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579`。均与提交包记录一致。
- 本步没有前端代码改动；未运行浏览器测试，原因是 F01/F02/N04 的受审改动均为后端算法/测试与数据证据。

## 最终判定

结论：**FAIL**。已登记的类别/具体同义词行为、F02、N04、回归和三份数据库保护证据通过；未知标签仍执行包含匹配，是明确的 P2 契约违例。另有 r01 包内历史证据被重写的 P2 审计完整性例外。

下一步：S04 状态登记为 `CHANGES_REQUIRED`，只允许提交新的 S04 整改轮；**不允许开始 S05**。历史证据例外需在 S04 最终 PASS 前获得用户接受或由原始备份补证。

台账登记后，r02 manifest 中唯一变化是本报告审查方更新的 `docs/review/STAGE_STATUS.md`：manifest 原 SHA `73134b95daedc5628eaf6a0ec54e6e9a288329776099f9fa98bcffa23d993760`，当前 SHA `3fbe1c60cae52137d6f7edc7f99e84a2f2724e652ca34d3035ae1a18453dfb10`；其余 151 项仍匹配。受审 manifest 指纹和提交证据包未改。
