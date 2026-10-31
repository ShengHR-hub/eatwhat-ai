# 开发交接清单（统一测试前）

日期：2026-10-29
状态：S11、G3、G4、G5 开发完成；测试统一后置。未执行冻结、展示壳、关机。

## 已完成

| 组 | 结果 | 证据 |
| --- | --- | --- |
| S11 | 6,400/6,400 打标成功；320 次调用一次通过；0 向量异常；$0.6965 估算 | `docs/review/consolidated/G2_R02/` |
| G3 | 48,000 次推荐、两臂各 24,000 流水、1,000 房 40,000 票；独立复算通过 | `docs/review/consolidated/G3/` |
| G4 | CRUD/真实打标/13 统计接口/DataManage/17 图大屏/筛选/下钻/PNG | `docs/review/consolidated/G4/` |
| G5 | Capacitor Android 工程、原生 HTTP/WS、应用图标、调试 APK | `docs/review/consolidated/G5/` |

## 关键产物

- APK：`docs/review/consolidated/G5/data/eatwhat-debug.apk`
- G3 benchmark：`docs/review/consolidated/G3/data/parallel_benchmark_full.json`
- S11 验收：`docs/review/consolidated/G2_R02/data/s11_verification.json`
- 冻结器：`scripts/freeze_release.py`（未执行）

## 统一测试顺序建议

1. 后端全量 `pytest -q`，处理既有 Windows symlink 环境用例。
2. 前端 build + `check-colors`。
3. `home-fit`、`refill-fresh`、`sandbox-sync`。
4. G4 大屏/管理页浏览器验收，含 15 个 PNG、筛选、下钻。
5. S11 抽检、G3 独立复算。
6. APK 真机安装、局域网 API/WS、权限/断网/扫码。
7. 全部通过后生成统一 `validation.json`，运行 `freeze_release.py`。
8. 冻结后再开发/启用展示壳，最后执行关机。

## 外部阻塞

- `VITE_AMAP_JS_KEY` 未配置：POI 地图保持明确空态，其余图表可用。
- 真机、相机扫码与断网重连尚未实测。
