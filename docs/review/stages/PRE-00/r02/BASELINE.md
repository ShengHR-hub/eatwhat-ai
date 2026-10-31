# PRE-00 / r02 基线

日期：2026-10-25（Asia/Shanghai）
工作目录：`D:\EatWhat`
基线采集：2026-10-25T13:24:27+08:00（`logs/00_baseline.txt`、`data/baseline.json`）
源码清单：`SOURCE_MANIFEST.json`，fingerprint `4d2187b64aced13445049807ec9f5b580da34e3d139dcb1dcadd267974a16361`（66 项）

## 1. 源码版本

| 项 | 值 |
| --- | --- |
| 分支 | `master` |
| HEAD | 不存在（`git rev-parse HEAD` 退出码 128，0 commit） |
| 工作区 | 采集时 staged 280 / unstaged 130 / untracked 52；均为开工前既有变更 + 本轮新增，未清理 |
| staged diff SHA-256 | `cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb` |
| 契约版本 | `MASTER_SPEC.md` v2.3.5 |
| 本轮改动 | 仅迁移脚本守卫与专项测试；r01 证据未覆盖 |

关键文件 SHA：

- 迁移脚本：`4554358c8f0a458c8e334f1ffd2ec3eb380a1ff1570dbeab4950b8c97e624369`（`pre00_runtime_v2`）
- 专项测试：`2c097b4f7166e895d0eed7d7078ef07fa36acc84c6097685fab1d5345026d09b`

## 2. 运行环境

| 组件 | 版本 |
| --- | --- |
| OS / Shell | Windows 10.0.22631 x64 / Git Bash |
| Python | 3.13.9 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |
| HTTPX | 0.28.1 |
| Uvicorn | 0.30.0 |
| pytest | 9.0.3 |
| Node / npm | v24.19.0 / 11.17.0 |

依赖声明仍为 `requirements.txt` 区间；前端本轮未构建，仅固定 `frontend/package.json`（`66e99826…48c49b`）与 `frontend/package-lock.json`（`adc87fc7…20c297`）。

## 3. 数据库身份

### 3.1 演示库 `backend/eatwhat.db`（只读）

| 项 | 值 |
| --- | --- |
| 大小 | 217,088 B |
| SHA-256 | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` |
| schema 指纹（迁移脚本同一算法） | `b708e1d2ef826dcb6d61a2e3e51e27d33b9ce5bae4ffc959b0881763d9e5228f` |
| 行数 | users 4 / restaurants 20 / dishes 100 / user_preferences 4 / fridge 12 / logs 9 / rooms 0 / votes 0 / algo_configs 1 |

### 3.2 S10 独立导入库 `backend/eatwhat_batch4.db`（只读）

| 项 | 值 |
| --- | --- |
| 大小 | 6,316,032 B |
| SHA-256 | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` |
| schema 指纹 | `ed2a27c840b12575d7fb7c5f8ec0f364ededd98aa04832af66ef39de0f866759` |
| 行数 | restaurants 7,664 / dishes 6,400 / 其余 0 |

### 3.3 开发运行库 `backend/eatwhat_dev_pre00_r02.db`

| 项 | 值 |
| --- | --- |
| 创建命令 | `cp backend/eatwhat.db backend/eatwhat_dev_pre00_r02.db` |
| 创建时间 | 2026-10-25T13:23:12+08:00（`logs/03_dev_copy_provenance.log`） |
| 迁移前 SHA | `775da775…bd3a60b`（与演示库字节一致） |
| 迁移后 SHA | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` |
| 二次迁移后 SHA | 同迁移后，字节不变 |
| schema 指纹 | `82f1b327dcd220dacf055cf57354454f03b2cfe7fa1809336bc3b4c036ccaeb7` |
| 行数 | 与演示库一致：4 / 20 / 100 / 12 / 9 / 0 / 0 |

说明：r01 的 `backend/eatwhat_dev_pre00.db` 仍是迁移后状态，仅作历史对照；r02 不复用它，也不覆盖它。

## 4. 服务基线

| 用途 | 地址 | 数据库 |
| --- | --- | --- |
| r02 迁移后验证 | `http://127.0.0.1:8034` | `sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db` |

启动命令（仓库根目录）：

```bash
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db" \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8034
```

服务验证后已停止；没有连接 `backend/eatwhat_batch4.db`。

## 5. 范围声明

- 本轮只整改 FAIL-01（文件身份守卫）并重跑迁移/接口/回归；
- 未改台账，未签 PASS，未进入 S00–S05；
- 未把 S10 大库接入演示流程；未验证 BRIDGE-10；
- 符号链接因本机权限无法实测，8.3 短路径未启用，均在 `validation.json.known_limits` 明示。
