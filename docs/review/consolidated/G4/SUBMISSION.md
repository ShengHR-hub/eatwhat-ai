# G4 开发交付：管理后台与实验大屏

- 状态：功能开发完成，统一验收留待最终阶段；不签 Codex PASS。
- 后端：`admin.py` CRUD/真实 LLM 打标，`admin_experiments.py` G3 正式输出适配，`admin_stats.py` 13 个统计接口。
- 前端：`/admin/data` 数据管理、`/admin/dashboard` 实验大屏；16 个 ECharts 可视项 + POI 地图项，合计 17 项；筛选、下钻、空态、PNG 导出。
- 数据：读取真实数据库、G3 隔离库与 `parallel_benchmark_full.json`，不预置演示曲线。

## 已完成的开发验证

- 23 条后台/统计定向测试通过。
- 前端生产构建通过；颜色门禁 51 文件通过。
- DataManage 浏览器流程通过：新增、编辑刷新持久化、未配置模型真实 503、软删除保留历史。
- 大屏正式 G3 曲线、16 个 canvas、PNG 文件导出及历史 ID 下钻均已跑通；统一最终回归按用户要求后置。

## 外部配置

POI 地图的 `VITE_AMAP_JS_KEY` 与 `VITE_AMAP_JS_SECURITY_CODE` 已配置到本地 `frontend/.env.local`（已 gitignore），并已重新构建 Web 与 APK。
