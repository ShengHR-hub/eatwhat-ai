# BASELINE — PC01 / R02（真实仿真与 benchmark 数据替换）

- 日期时区：2026-10-24 16:20（Asia/Shanghai）
- 工作区状态：**无 Git 提交**（git rev-parse HEAD → $head；当前分支 $branch）；工作树改动条目 314 条（全部为 staged 新增 + 少量 unstaged 修改）
- 版本固定方式：按 docs/REVIEW_RULES.md §5，用 SOURCE_MANIFEST.json（15 个受审文件的 SHA-256）+ git status --short 固定，未执行 git add . / git commit / git reset
- 环境：Node v24.19.0 / npm 11.17.0 / Python Python 3.13.9 / Windows（PowerShell 7）
- 数据集身份：ackend/eatwhat.db
  - 种子：20 门店 / 100 菜品（外食 60、下厨 40）/ 4 演示角色
  - lgo_configs 仅 1 行 default_production
  - 库文件 SHA-256 见 SOURCE_MANIFEST.json（ackend/eatwhat.db）
- 仿真输入身份：docs/review/stages/PC01/r01/data/benchmark_seed20261024.json（seed=20261024、λ=0.5、ω=0.5）与 enchmark_seed7.json（seed=7、λ=0.8、ω=0.6）
- 说明：R02 只改数据与脚本，不涉及 UI；rowser/ 目录为空并在 SUBMISSION.md 说明原因。
