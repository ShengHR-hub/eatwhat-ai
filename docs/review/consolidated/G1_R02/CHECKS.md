# G1-R02 执行记录

范围：只整改 S07 的 Lottie 揭晓欠项；不覆盖 G1/G2 原提交包，不改正式审查结论。

## 最终有效检查

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| `node docs/review/consolidated/G1_R02/browser/lottie_reveal.mjs` | 真实建房→开局→超时揭晓；9/9 path 已绘制且位于组件矩形内，动画推进，无 console/exception，exit 0 | `logs/13_lottie_reveal_static_position.log` |
| `npm run build`（frontend） | 824 modules，exit 0 | `logs/30_frontend_build_final.log` |
| `node scripts/home-fit.mjs` | 390×844 / 390×667 均 PASS | `logs/31_home_fit.log` |
| `node scripts/refill-fresh.mjs` | PASS | `logs/32_refill_fresh.log` |
| `node scripts/sandbox-sync.mjs` | PASS | `logs/33_sandbox_sync.log` |
| `node scripts/check-colors.mjs` | 38 文件无裸色值，exit 0 | `logs/34_check_colors.log` |
| `python scripts/check_lottie_colors.py` | exit 0 | `logs/35_lottie_colors.log` |
| `python docs/review/consolidated/G1_R02/data/probe_db_protection.py` | 7 个受保护库 SHA 均未变，输出只写 G1_R02 | `logs/42_db_protection_isolated.log` |

## 诊断过程保留

- `logs/10–12` 保留了接入后仍不可见、结束帧调整无效等失败记录；它们不是最终通过证据。
- 最终有效版本使用静态圆点坐标与透明度关键帧，成功记录为 `logs/13`。
- 最终截图：`browser/shots/reveal_lottie_visible.png`；结构化结果：`browser/lottie_reveal.json`。
- 数据库探针首次调用受管理 Python 缺少 `tzdata` 影响，改用项目既有 Python 后通过；最终探针输出独立写入 `G1_R02/data/db_protection.json`。
- **证据例外**：首次成功调用旧探针时回写了 `G1/data/db_protection.json`，原始字节未能恢复；旧 manifest 预期 SHA `81239287…f1f`，当前 `fb991f17…38de`。不伪造恢复，详见 `SUBMISSION.md` §5。
- S09/r04 只读封存复核：90 项 manifest、80 项 snapshot、0 失配、0 封存后写入，见 `logs/43_s09_seal_verify.log`。

## 不在本轮关闭的事项

1. 真机相机扫码仍 BLOCKED。
2. 断线后不依赖整页重载的继续投票与结算幂等仍 BLOCKED。
3. S11 真实打标仍 BLOCKED；G3 未获放行。
