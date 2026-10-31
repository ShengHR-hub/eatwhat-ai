# CHECKS —— PC03/r02

命令、工作目录、退出码与日志一一对应；时间取日志文件最后写入时间（`mtime`），不是人工填写。

| # | 命令 | cwd | 时间 | 退出码 | 日志 | 备注 |
|---|---|---|---|---|---|---|
| 1 | `node scripts/check-colors.mjs` | `.` | 17:46:57 | 0 | `logs/20_check_colors_pass.log` | 全绿：34 个文件 |
| 2 | `node scripts/check-colors.mjs（临时塞入 _gate_probe.css）` | `.` | 17:46:58 | 1 | `logs/21_check_colors_block_css.log` | 反例：CSS 里 3 处裸色值被拦 |
| 3 | `node scripts/check-colors.mjs（临时塞入 bits/_fake_business.vue）` | `.` | 17:46:58 | 1 | `logs/22_check_colors_block_bits.log` | 反例：非上游 bits 文件被拦 |
| 4 | `node scripts/check-colors.mjs` | `.` | 17:46:58 | 0 | `logs/23_check_colors_after_cleanup.log` | 清掉探针后回到全绿 |
| 5 | `cd frontend && npm run build` | `frontend` | 17:47:09 | 0 | `logs/24_build.log` | 构建通过 |
| 6 | `node scripts/home-fit.mjs` | `.` | 17:47:12 | 0 | `logs/25_home_fit.log` | 两档屏高一屏门禁 PASS |

## 未执行的检查项

| 检查 | 状态 | 原因 |
|---|---|---|
| 视觉回归（像素 diff） | 未执行 | 项目还没有视觉基线工具；当前用三张实拍 + 人工对照 |
