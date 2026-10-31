# S02 / r02 独立复审报告

审查时间：2026-10-26（Asia/Shanghai）  
审查方：Codex  
受审包：`docs/review/stages/S02/r02/`  
受审 manifest：146 项，fingerprint `2c8cc39df3a00c8f11c15ecf77d768da47e969447ba6a4fb5140885829c9556a`

## 最终结论

**S02/r02：PASS。**

## 独立核验

| 条目 | 实际结果 | 结论 |
| --- | --- | --- |
| 证据身份 | 146 项全部存在，逐项 SHA-256 与字节数匹配，无重复路径 | PASS |
| manifest 指纹 | 按 `data/build_manifest.py` 的路径与 SHA 列表算法重算，与 `2c8cc39d…c9556a` 一致 | PASS |
| 历史非法值守卫 | `backend/routers/auth_user.py` 的 `_validated_history_vector()` 在任何字段赋值前执行；未知键、非对象、布尔、非数字、NaN/Infinity、越界值返回 409 | PASS |
| r01 阻断场景一 | 隔离内存库：历史 `spicy_level=95` + 仅改预算返回 409；预算、向量及其他偏好快照不变 | PASS |
| r01 阻断场景二 | 隔离内存库：历史含 `umami_level` + 合法部分向量返回 409；未知键保留，快照不变 | PASS |
| 合法缺键语义 | 合法两键历史 + 预算更新返回 200；向量补齐为八键，缺失维度为 0.5，预算写入 | PASS |
| 专项回归 | `python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider`：96 passed | PASS |
| 后端全量回归 | 仓库内独立 `--basetemp`：306 passed, 1 skipped，exit 0 | PASS |
| 受保护库 | 未连接或写入演示库、S10 库、开发源库；manifest 中三库基线与包内记录一致 | PASS |

专项探针实际输出：

```json
[
  {"case":"illegal history + budget-only","status":409,"unchanged":true},
  {"case":"unknown history + partial vector","status":409,"unchanged":true,"unknown_retained":true},
  {"case":"legal incomplete history + budget-only","status":200,"eight_keys":true,"filled_neutral":true,"budget_written":true}
]
```

全量测试若使用默认 Windows pytest 临时目录，会因本机目录权限产生 `PermissionError`；使用仓库内独立 `--basetemp` 后完整通过。该环境问题不属于代码失败，提交包的隔离运行方式与此一致。

manifest 的 146 项匹配是在审查登记台账之前独立验证的。PASS 登记随后更新了 `docs/review/STAGE_STATUS.md`；该台账文件本身列在提交 manifest 中，因此登记后其工作区哈希会与提交时版本不同。此差异仅由本次审查状态登记造成；受审代码文件与其 manifest 哈希未改动，提交包仍由原 manifest 指纹绑定。

## 残留风险

- 全量回归保留 1 个既有 Windows 符号链接权限 skip；本步未新增 skip。
- 测试与隔离 HTTP 运行产生的数据库均不在受保护演示库、S10 库或开发源库中。
- S02 范围外的 S03–S10、`/admin`、多人 WS 和 APK 未在本步验收。

## 放行

S02/r02 的两项 r01 阻断已闭合，允许下一步 **S03** 开始。开发方仍不得自行修改台账；台账更新应由 Codex 流程按本报告登记 `S02=PASS`、`S03=READY`。
