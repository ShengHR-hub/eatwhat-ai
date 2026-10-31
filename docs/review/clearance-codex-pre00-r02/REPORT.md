# PRE-00/r02 独立复审报告

日期：2026-10-25（Asia/Shanghai）  
受审包：`docs/review/stages/PRE-00/r02/`  
受审 manifest：66 项，fingerprint `4d2187b64aced13445049807ec9f5b580da34e3d139dcb1dcadd267974a16361`  
结论：**PASS**

## 复审范围

本轮只复审 r01 的 FAIL-01 文件身份保护整改，以及 PRE-00 原有的迁移、回滚、幂等、接口恢复和原库保护。未把 S00–S08、前端 build、浏览器、双校区过滤或 S10 业务实现算作 PRE-00 通过条件。

## 独立核验

| 项目 | 结果 | 独立结果 |
|---|---|---|
| manifest | PASS | 66 项逐文件 SHA 核对，0 失配 |
| 文件身份守卫 | PASS | `_guard_path()` 使用 `os.path.samefile()`；真实硬链接和大小写别名均拒绝 |
| CLI 硬链接反例 | PASS | 演示库/S10 副本硬链接别名均 exit 1，副本状态不变 |
| 原库保护 | PASS | 演示库 SHA `775da775…bd3a60b`、S10 库 SHA `315eb3da…6918c28` 未变化；schema、行数和旁文件均不变 |
| 全新副本迁移 | PASS | 18 个可空列补齐，`feature_vector` 放宽，20 门店/100 菜/0 房保留，外键检查为空 |
| 幂等 | PASS | 第二次迁移 `idempotent=true`，`added_columns=[]`、`rebuilt_tables=[]`，SHA 字节不变 |
| API | PASS | 独立服务：health、外食推荐、下厨推荐、足迹、冰箱均 200，推荐各 5 条 |
| 回归 | PASS | 迁移专项 `7 passed, 1 skipped`；隔离全量 `175 passed, 1 skipped` |

## FAIL-01 复验

源码 `backend/scripts/migrate_pre00_runtime_schema.py` 当前守卫先确认目标是存在的普通文件，再对演示库和 S10 库调用 `os.path.samefile()`。独立 UTF-8 环境运行真实探针得到：

```text
demo hardlink: samefile=true, resolved_paths_equal=false, guard raised=true
s10 hardlink:   samefile=true, resolved_paths_equal=false, guard raised=true
demo CLI alias: exit_code=1, state_unchanged=true
s10 CLI alias:   exit_code=1, state_unchanged=true
case alias:      guard raised=true
originals_unchanged=true
```

这关闭了 r01 报告指出的“通过硬链接改写受保护数据库”路径。全新副本上的首次迁移和第二次迁移也均由本轮独立执行确认。

符号链接在当前 Windows 账户创建时返回 `WinError 1314`，专项测试明确 skip，提交包没有把它伪装成已实测通过。由于 `samefile` 对符号链接解析到目标文件身份，且硬链接已覆盖相同的别名身份绕过面，本限制不构成 PRE-00 的阻断项。

## 复现环境注意事项

Windows PowerShell 默认 CP936 环境下，提交包的子进程探针若未设置 UTF-8，可能在读取拒绝信息时出现探针自身的解码异常；设置 `PYTHONIOENCODING=utf-8` 后探针完整通过。该问题属于证据脚本的输出编码可复现性，不影响迁移守卫和数据库状态；后续可在证据工具中改为显式 `errors="replace"` 或使用系统编码。

## 放行范围

PRE-00/r02 **PASS**，r01 FAIL-01 已关闭。该结论使 PRE-00 具备进入 S00 的条件；S00、S01–S08 和 S10 仍必须按各自步骤由 Codex 独立审查，不能由本报告直接视为通过。前端 build、真实浏览器和首页专项未在本轮审查。

本报告为新文件，未覆盖 r01 报告。Codex 签发 PASS 后已更新 `docs/review/STAGE_STATUS.md`：PRE-00 登记 PASS、S00 设为 READY；S10 暂锁至 PRE-S10 计划的 BRIDGE-10 PASS，既有 S10/r01 证据保留。manifest 的 66 项 0 失配核验发生在台账登记前；台账随后按本报告更新，故该项现在与提交时基线不同。未修改业务代码或数据库。
