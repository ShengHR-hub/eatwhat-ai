# SQLite → PostgreSQL 迁移手册

日期：2026-10-30  
对应阶段：后台重规划 · 阶段 A/B 的「地基」部分

## 1. 这套东西解决什么问题

原来后台只有一句话：启动时 `create_all()` 建表，库是 `backend/eatwhat.db` 一个文件。
问题有三个：

1. **改模型就等于改生产库**——重启一次，生产表结构就跟着代码跑偏，没有留痕、没法回滚。
2. **SQLite 只适合一个人用**——多人同时投票、结算时写锁会打架。
3. **备份只能拷文件**——拷的过程中有人写入，拷出来的是半个状态。

现在换成：结构由 Alembic 管，数据搬到 PostgreSQL。

## 2. 目录与文件

```text
backend/
├── alembic.ini                      # 配置（ASCII-only，见 §6 坑 1）
├── migrations/
│   ├── env.py                       # 连接串唯一来源：backend/config.py
│   └── versions/
│       ├── 022b1382298a_baseline_schema.py   # 11 张表的基线
│       └── 5974c7e57e83_add_user_role.py     # users.role
├── scripts/
│   ├── sqlite_to_postgres.py        # 数据搬家
│   └── grant_admin.py               # 管理员角色开关
└── database.py                      # AUTO_CREATE_SCHEMA 开关
```

## 3. 日常命令

```bash
# 在 backend/ 目录下执行
cd backend

# 看当前版本
python -m alembic current

# 升到最新
python -m alembic upgrade head

# 回退一步 / 回退到底
python -m alembic downgrade -1
python -m alembic downgrade base

# 改完 models.py 后生成迁移（务必先 upgrade head，否则基线会混进新改动）
python -m alembic revision --autogenerate -m "说明"

# 检查模型与库是否有差异（只在目标库上跑，见 §6 坑 3）
python -m alembic check
```

连接串优先级：`-x db_url=...` > 环境变量 `DATABASE_URL` > `backend/.env`。
想临时指向别的库，不用改文件：

```bash
DATABASE_URL=postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat python -m alembic upgrade head
```

## 4. 搬家四步

```bash
# 0) 起开发用 PG（生产换成自己的实例，不要用这份 compose）
docker compose -f docker-compose.dev.yml up -d

# 1) 目标库建结构
DATABASE_URL=postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat \
  python -m alembic upgrade head

# 2) 先看要搬多少，不写库
python -m backend.scripts.sqlite_to_postgres \
  --target postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat --dry-run

# 3) 真搬（目标表非空会拒绝；确认要覆盖加 --truncate）
python -m backend.scripts.sqlite_to_postgres \
  --target postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat

# 4) 核对行数
python -m backend.scripts.sqlite_to_postgres \
  --target postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat --verify
```

搬完把 `backend/.env` 的 `DATABASE_URL` 换成 PG 那行，重启后端即可。
PostgreSQL 下 `AUTO_CREATE_SCHEMA` 默认是关的，后端不会再偷偷建表。

## 5. 搬家脚本的三个硬约束

| 约束 | 为什么 |
|---|---|
| 保留主键 | 房间号、投票、流水都靠 id 互相关联，重新编号会断链 |
| 按外键顺序插入 | 用 SQLAlchemy metadata 的拓扑排序，不手写顺序 |
| 搬完 `setval` | PG 自增序列不认显式插入的 id，不重置下一条 INSERT 必撞主键 |

另外它做了类型转换：旧库 `appliance_tag` 是 `VARCHAR(32)` 存 JSON 字符串
（`'["炒锅"]'`），目标库是 JSON 列，脚本会 `json.loads` 再 `json.dumps` 回写，
裸文本（如 `炒锅`）会兜底包成 `["炒锅"]`。

## 6. 踩过的坑

1. **`alembic.ini` 必须纯 ASCII。**
   configparser 用系统 locale 读文件（Windows 是 GBK），写中文注释会直接
   `UnicodeDecodeError`，连 `alembic --help` 都跑不起来。

2. **旧库有三处结构漂移，不能当成「模型就是库」。**
   - `dishes_and_recipes.appliance_tag`：库里是 `VARCHAR(32)`，模型是 `JSON`
   - `dishes_and_recipes.feature_vector`：库里 `NOT NULL`，模型允许 NULL（当前 0 行为空）
   - `room_votes` 唯一性：库里是唯一索引 `uq_room_votes_room_user_dish`，
     基线建的是表级唯一约束（语义等价）

   基线以**模型意图**为准，旧库用 `alembic stamp head` 认账，不回头改旧库。

3. **`alembic check` 只对目标库有意义。**
   拿它去查旧 SQLite 会报上面那三处漂移，那是历史包袱不是新问题。

4. **现有库不要 `upgrade` 从零建。**
   已经存在的库先 `alembic stamp head`（记录"已在基线版本"），再 `upgrade`。

5. **`text()` 里不能写裸 `%s`。**
   psycopg 方言用 pyformat 占位，SQLAlchemy 会把 `%s` 转义成 `%%s`，SQL 直接
   语法错误。必须用命名参数 `:v0` 配 `CAST(:v0 AS json)`。第一版就是栽在这里，
   报错长这样：

   ```text
   ProgrammingError: syntax error at or near "%"
   [SQL: INSERT INTO "algo_configs" (...) VALUES (%%s, %%s, ...)]
   ```

## 7. 当前验证状态（2026-10-30 实测）

| 项目 | 状态 |
|---|---|
| 基线迁移建出 11 张表 | ✅ SQLite + PostgreSQL 均验过 |
| 迁移与模型无差异（`alembic check`） | ✅ 两边都无差异 |
| 可回滚（`downgrade base` → `upgrade head`） | ✅ PG：12 表 → 1（仅 alembic_version）→ 12 |
| 现有库 `stamp head` | ✅ `current` 显示 head |
| 角色字段迁移 | ✅ 已应用到 SQLite 运行库与 PG |
| 搬家 14,311 行 | ✅ 11 张表行数逐表一致 |
| JSON 字段转换 | ✅ `appliance_tag` 落库为 JSON 数组（`["炒锅"]`），中文无乱码 |
| 自增序列重置 | ✅ 不指定 id 插入拿到 7（原最大 6），未撞主键 |
| PG 上跑真实接口 | ✅ `/health` db=ok；外食推荐 200（砂锅豆腐 83.8 分）；下厨推荐 200；profile 200；登录 200；普通用户访问管理接口 403 |

实测环境两套都跑通了：

- **Docker 版**：PostgreSQL 16.15（`docker-compose.dev.yml`，端口 5433）——本机 Docker 不稳定，已降级为备用
- **原生版（当前运行库）**：PostgreSQL 16.15，程序 `D:\PostgreSQL\16`，数据 `D:\PGData\16`，端口 5433

> 结论：地基这一步**已验证通过**，运行库已切到原生 PostgreSQL。

## 8. 原生安装（当前方案）

官方安装程序在本机会失败：它会把自己解压到 `C:\Users\盛浩然\AppData\Local\Temp\`，
路径含中文，PowerShell 以 GBK 码页执行脚本时报 `getlocales.ps1` 编码错误，
且提权后不继承 `set TEMP` 的临时改动。

改用免安装包，完全绕开安装脚本：

```text
下载  https://get.enterprisedb.com/postgresql/postgresql-16.15-5-windows-x64-binaries.zip
解压  解压后把 pgsql 目录改名为 D:\PostgreSQL\16
初始化 D:\PostgreSQL\16\bin\initdb.exe -D D:\PGData\16 -U postgres -E UTF8 --locale=C --pwfile=...
改配置 pg_hba.conf 本机连接从 trust 改成 scram-sha-256；postgresql.conf 设 port=5433、listen_addresses='127.0.0.1'
启动  D:\PostgreSQL\16\bin\pg_ctl.exe -D D:\PGData\16 -l D:\PGData\16\server.log start
建库  create role eatwhat login password '...'; create database eatwhat owner eatwhat encoding 'UTF8';
```

启停脚本：`D:\PGData\start-pg.bat` / `stop-pg.bat`。

**注册成 Windows 服务**（需要管理员权限，一次即可，之后开机自启）：

```bat
"D:\PostgreSQL\16\bin\pg_ctl.exe" register -N postgresql-16 -D "D:\PGData\16" -S auto
```

不注册也能用，只是每次开机要手动跑一次 `start-pg.bat`。
