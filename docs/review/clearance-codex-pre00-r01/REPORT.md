# PRE-00/r01 独立复审报告

日期：2026-10-25（Asia/Shanghai）  
受审包：`docs/review/stages/PRE-00/r01/`  
结论：**FAIL（需整改后复审）**

## 复审范围

本轮只审 PRE-00 运行库兼容层：迁移脚本、开发库副本、演示库/S10 原库保护、接口恢复、事务回滚、幂等性和后端回归。未把 S00–S08、前端 build 或双校区过滤算入 PRE-00 通过条件。

## 独立核验结果

| 项目 | 结果 | 证据 |
|---|---|---|
| r01 manifest | PASS | 66 个文件逐个 SHA 核对，0 失配 |
| 开发库二次迁移 | PASS | `migrate_pre00_runtime_schema --db backend/eatwhat_dev_pre00.db` 返回 `idempotent=true`，SHA 不变 |
| 全新演示库副本迁移 | PASS | 18 个可空字段补齐，`feature_vector` 放宽，20 门店/100 菜/0 房保留 |
| 旧数据保留 | PASS | 三张关键表旧列值逐行相同，原索引和外键保留，`foreign_key_check=[]` |
| 接口恢复 | PASS | 隔离服务 8033：`/health`、外食推荐、下厨推荐、足迹、冰箱均 200 |
| 回归测试 | PASS | 迁移专项 `5 passed`；隔离全量后端 `173 passed` |
| 原库普通路径保护 | PASS | `eatwhat.db` 与 `eatwhat_batch4.db` SHA 保持 `775da7...` / `315eb3...` |
| 原库身份保护 | **FAIL** | 硬链接绕过路径守卫，可改动受保护文件 |

## FAIL-01：保护守卫可被硬链接绕过（P1）

源码：`backend/scripts/migrate_pre00_runtime_schema.py:175-184`。

`_guard_path()` 只比较 `Path(db_path).resolve()` 与两个固定路径。Windows NTFS 硬链接拥有不同路径但指向同一 inode，因此 `resolve()` 后仍不相等。独立探针在工作区临时目录创建一个演示库副本的硬链接，将 `m.DEMO_DB` 指向原文件路径后调用 `migrate(alias)`，结果为：

```text
samefile=true
resolved_paths_equal=false
migration_allowed=true
sha_changed_via_alias=true
```

该探针只改动临时文件；原始 `backend/eatwhat.db` 和 `backend/eatwhat_batch4.db` 未被触碰。但行为证明“拒绝迁移演示库/S10 原库”的安全边界不是由文件身份而是由字符串路径决定，攻击者或误操作可通过硬链接绕过并修改受保护原库。该问题直接违反 PRE-00 的原库保护验收，故本步不能 PASS。

## 下一轮整改要求

1. 在迁移入口按文件身份拒绝受保护数据库：至少对现有路径和目标路径使用 `os.path.samefile()`/等价 Windows 文件身份校验；同时处理符号链接、硬链接和大小写/短路径别名。不能只继续增加字符串路径黑名单。
2. 增加真实硬链接（以及可用时的符号链接）反例测试：迁移必须退出码 1，受保护文件 SHA、schema 和行数全部不变。
3. 重新运行迁移专项、隔离全量后端测试、开发库三接口验证，并生成新的 `PRE-00/r02/` 证据包；不得覆盖 r01。
4. 提交后停手，等待 Codex 独立复审。执行方不得修改台账或自行开放 S00。

## 其他限制

本轮没有测试前端 build、真实浏览器、S05/S08 或双校区 campus 过滤；这些仍按 `PRE_S10_REMEDIATION_PLAN.md` 的后续步骤处理。PRE-00 FAIL 不改变 S09 已有历史结论，也不授予 S00 或 S05 放行。
