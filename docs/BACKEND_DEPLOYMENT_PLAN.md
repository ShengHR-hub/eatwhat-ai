# 后台功能与部署重规划

日期：2026-10-30  
状态：规划稿。APK 构建暂缓，先解决后台能否稳定部署、能否支撑真实用户。

## 1. 当前后台

- FastAPI + SQLAlchemy + SQLite 单文件
- 身份：`X-User-Id` 请求头，属于演示身份，不是认证
- 房间：进程内 WebSocket Hub + SQLite 房间/投票表
- 识别：后端直接调用智谱视觉模型
- 天气：高德优先，Open-Meteo 兜底
- 配置：`backend/.env` 自动加载
- CORS：已改为 `CORS_ORIGINS` 环境变量；本地默认 `*`，生产必须白名单
- 无 Alembic 迁移、无管理员鉴权、无 Redis、无对象存储、无限流

## 2. 上线前必须解决

### 2.1 身份认证

`X-User-Id` 只能用于演示。真实部署必须换成：

- 手机号验证码 + JWT，或
- 微信登录 / 微信小程序登录，或
- 学校统一身份（如果学校提供）

后端保留 `user_id` 语义，但由 token 解析，不再信任请求头。

### 2.2 数据库

- 演示：SQLite 可以继续用
- 部署：PostgreSQL
- 引入 Alembic，禁止启动时 `create_all` 直接改生产库
- 备份策略：每日全量 + 关键表增量
- 房间/投票/流水保留审计字段

### 2.3 实时房间

当前 Hub 在单进程内存里，多 worker 会丢广播。上线需要：

- Redis Pub/Sub 或 Redis Streams
- 房间状态仍落 PostgreSQL
- WebSocket 断线重连、幂等结算
- 15 秒截止以服务端时间为准

### 2.4 图片与识别

- 上传图片默认不长期保存
- 如需保存，使用对象存储（OSS/S3/COS），设置 7 天生命周期
- 视觉模型调用增加：
  - 6MB 限制
  - 20 秒超时
  - 失败重试一次
  - 用户级/全局限流
  - 成本上限
- 识别结果必须用户确认后才入库

### 2.5 管理后台

`/admin` 现在没有独立鉴权。上线前至少：

- 管理员 token 或角色表
- 管理接口与普通用户接口分离
- 导出、重算、删除等高风险操作二次确认
- 审计日志

### 2.6 可观测性

- 结构化日志：request_id、user_id、route、latency、status
- 健康检查：`/health` 增加 DB 检查
- 慢查询日志
- 视觉模型调用耗时/失败率
- 房间结算失败告警

## 3. 目标架构

```text
Capacitor / Web
      │ HTTPS
      ▼
Caddy / Nginx
      │
      ▼
FastAPI (uvicorn/gunicorn)
  ├── PostgreSQL  用户、菜谱、门店、流水、房间
  ├── Redis       房间广播、限流、短期缓存
  ├── 对象存储     可选，识别图片/用户背景图
  └── 视觉模型     OpenAI 兼容端点
```

## 4. 分阶段

### 阶段 A：单机可部署

- 生产 `.env`
- CORS 白名单
- HTTPS 反向代理
- PostgreSQL 或受保护 SQLite
- 每日备份
- 健康检查 + 日志
- 不构建 APK，先用浏览器验证

### 阶段 B：真实身份

- 登录/注册
- JWT
- 用户与演示身份解耦
- 管理后台鉴权

### 阶段 C：多实例与实时

- Redis Pub/Sub
- 房间状态迁移
- WebSocket 多实例验证
- 限流与成本控制

### 阶段 D：数据与体验

- 真实门店菜单来源
- 识别结果质量评估
- 房间逐用户五维匹配的天气快照
- 清理测试数据
- 回归测试

### 阶段 E：APK

只有 A–D 稳定后再构建 APK。否则 APK 下载后没有可用后台，功能仍然不可用。

## 5. 数据边界

- 门店 7,704：真实 POI + 建大/思源 fixture 门店
- 菜谱 6,560：6,440 下厨 + 120 外食 fixture
- 真实 7,664 家门店没有菜单，按 `docs/MENU_STRATEGY.md` 的分层策略只做 POI，不进入外食推荐
- 如要补菜单，必须明确来源：
  - 真实菜单：需要授权数据源
  - 合成菜单：标记 `synthetic_menu_v1`，不能当真实菜单宣传

## 6. 需要用户决策

1. 登录方式：手机号 / 微信 / 学校账号
2. 部署位置：云服务器 / 学校服务器 / 本地内网
3. 域名与 HTTPS
4. 真实门店菜单是否有数据源
5. 管理后台是否需要独立账号体系

## 7. 当前不做

- 不构建 APK
- 不伪造真实门店菜单
- 不在没有认证的情况下开放公网管理接口
- 不把演示 `X-User-Id` 当成生产认证

## 8. 执行进度（2026-10-30 更新）

### 已完成

| 项 | 状态 | 证据 |
|---|---|---|
| 账号密码注册/登录（PBKDF2 + Bearer token） | ✅ | `backend/routers/auth_local.py`，token 只存 SHA-256 哈希，7 天过期 |
| Alembic 接入，基线迁移 11 张表 | ✅ | `backend/migrations/versions/022b1382298a_*.py` |
| 迁移可回滚 | ✅ | SQLite：11 表 → `downgrade base` → 0 表 → `upgrade head` → 11 表 |
| 现有库认账（stamp） | ✅ | `alembic current` = head |
| `create_all` 收口 | ✅ | `AUTO_CREATE_SCHEMA`：SQLite 默认开、PG 默认关 |
| 数据搬家脚本 | ✅ 代码就绪 | `backend/scripts/sqlite_to_postgres.py`，转换逻辑单测过 |
| 管理后台鉴权 | ✅ | `require_admin` + 三个 admin router 挂依赖，四象限验过 |

管理接口鉴权验收（`testuser` 提为 ADMIN 后实测）：

| 请求 | 结果 |
|---|---|
| 不带 token | 401 |
| 只带 `X-User-Id: 5`（伪造管理员身份） | **401**（管理接口故意不认这个头） |
| 普通用户 token | 403 |
| 管理员 token | 200 |
| 普通用户访问 `/admin/stats/*` | 403 |

### 待补

- PostgreSQL 注册为 Windows 服务（`pg_ctl register`，需管理员一次）；当前靠后台进程 + 启动脚本
- 阶段 A 剩余：Caddy HTTPS 实机验证、日志切分（按天/按大小）
- 管理后台 UI 尚未处理 401/403（接口已拦，页面还是白屏式报错）——属于阶段 3

### 运行库切换：原生 PostgreSQL（2026-10-30 完成）

Docker 引擎当天崩了四次（WSL 内存不足），放弃用容器当运行库，改为原生安装：

| 项 | 值 |
|---|---|
| 版本 | PostgreSQL 16.15（与容器版同版本，迁移已验证） |
| 程序 | `D:\PostgreSQL\16` |
| 数据 | `D:\PGData\16` |
| 端口 | 5433（只听 127.0.0.1） |
| 认证 | `scram-sha-256`（安装脚本默认 `trust`，已改掉） |
| 启停 | `D:\PGData\start-pg.bat` / `stop-pg.bat` |

安装程序失败原因：中文用户名导致 PowerShell 执行 `getlocales.ps1` 编码错误，
改用官方免安装 zip + `initdb` 手工初始化。细节见 `docs/MIGRATION_SQLITE_TO_PG.md` §8。

验证结果：`/health` db=ok、外食推荐 200（砂锅豆腐 83.8，与 SQLite 一致）、登录 200、
14,311 行数据逐表核对一致。`docker-compose.dev.yml` 降级为备用方案。

### 审计日志（2026-10-30 完成）

- 表 `admin_audit_logs`：user_id / action / resource_type / resource_id / summary / detail(JSON) / ip / created_at
- 迁移 `0a755691cec1`；已应用到运行库
- 埋点覆盖 7 个写接口：门店增改删、菜品增改删、批量打标
- 查询接口 `GET /admin/audit-logs`（分页 + action/resource_type/user_id 过滤），仅管理员
- 设计取舍：**只记写操作不记查询**——查一次就写一行会让表迅速膨胀，且查询不改数据
- 实测：建店 → 改价 → 删店，三条记录齐全（含操作人昵称、IP、改前改后字段）；
  普通用户访问返回 403；测试数据已清理，门店数回到 7,704

> 注意：PG 实例里还没有 `admin_audit_logs`（数据是在加表之前搬的）。
> Docker 恢复后需要补跑 `alembic upgrade head`。

### PostgreSQL 实机验证（2026-10-30 完成）

环境：PostgreSQL 16.15（`docker-compose.dev.yml`，端口 5433）

| 项目 | 结果 |
|---|---|
| `alembic upgrade head` | 12 张表（11 业务表 + alembic_version） |
| `alembic check` | 与模型无差异 |
| 数据搬家 | 14,311 行，11 张表逐表行数一致 |
| JSON 转换 | `appliance_tag` 为 JSON 数组 `["炒锅"]`，中文无乱码 |
| 序列重置 | 不指定 id 插入得到 7（原最大 6） |
| 回滚 | 12 表 → 1（仅 alembic_version）→ 12 |
| 接口冒烟 | health `db=ok`；外食推荐 200（砂锅豆腐 83.8）；下厨 200；profile 200；登录 200；普通用户访问管理接口 403 |

### 迁移时发现的结构漂移

旧 SQLite 与 `models.py` 有 3 处不一致，基线以**模型意图**为准，
旧库通过 `stamp head` 认账，不回头改：

1. `dishes_and_recipes.appliance_tag`：库里 `VARCHAR(32)`，模型 `JSON`
2. `dishes_and_recipes.feature_vector`：库里 `NOT NULL`，模型允许 NULL
3. `room_votes` 唯一性：库里唯一索引 vs 基线表级唯一约束（语义等价）

### 下一步（阶段 B 剩余）

1. 把运行库正式切到 PostgreSQL（并行跑一段再切）
2. 管理后台页面重设计：登录态、角色可见性、审计日志
3. 高风险操作二次确认（删除门店/菜品、批量重算）
