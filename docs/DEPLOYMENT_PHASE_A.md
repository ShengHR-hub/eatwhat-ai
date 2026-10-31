# 阶段 A：单机可部署运行手册

日期：2026-10-30  
目标：先把后台稳定跑在一台服务器上，APK 暂缓。

## 1. 适用边界

- 单台服务器、单个 uvicorn worker
- SQLite 继续作为数据库
- 房间实时广播只在该进程内有效
- 不开放公网管理后台
- 不承诺多实例、高并发

多 worker / 多实例前必须完成 Redis 房间广播与 PostgreSQL 迁移。

## 2. 环境变量

复制模板：

```bash
cp backend/.env.example backend/.env
```

至少确认：

```env
DATABASE_URL=sqlite:////绝对路径/eatwhat.db
CORS_ORIGINS=https://你的域名,http://localhost:5173
VISION_API_KEY=...
VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
VISION_MODEL=glm-4v-flash
```

生产不要使用：

```env
CORS_ORIGINS=*
```

## 3. 启动

本地：

```bash
cd D:\EatWhat
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

服务器建议只监听本机，由反向代理对外：

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

不要在当前阶段开多个 worker。

## 4. 健康检查

```http
GET /health
```

正常：

```json
{"status":"ok","version":"2.3.2","db":"ok"}
```

数据库不可用：

```json
{"status":"degraded","version":"2.3.2","db":"error"}
```

反向代理或容器探针应检查 HTTP 200。

## 5. 反向代理

Caddy 示例：

```caddy
eatwhat.example.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

Nginx 需要额外配置 WebSocket 升级头：

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 120s;
}
```

## 6. 备份

在线备份：

```bash
python backend/scripts/backup_db.py --keep 14
```

建议 cron / 计划任务每天一次：

```cron
0 3 * * * cd /srv/eatwhat && python backend/scripts/backup_db.py --keep 14 >> logs/backup.log 2>&1
```

恢复：

1. 停服务
2. 把备份复制回 `eatwhat.db`
3. 启动并检查 `/health`
4. 抽查用户、菜谱、门店计数

## 7. 日志

当前 uvicorn 输出到标准输出。部署时重定向到文件：

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 \
  >> logs/api.log 2>&1
```

至少保留：

- 启动/停止
- 5xx
- 房间结算失败
- 视觉模型超时/失败

## 8. 上线前检查

- [ ] CORS 白名单
- [ ] HTTPS 生效
- [ ] `/health` 返回 db=ok
- [ ] 备份脚本跑过一次
- [ ] 管理员接口未暴露公网
- [ ] 视觉模型 Key 不在代码/仓库
- [ ] 单 worker
- [ ] 测试房间已清理

## 9. 回滚

1. 停止新进程
2. 恢复上一份数据库备份
3. 启动旧版本代码
4. 检查 `/health` 和首页推荐

## 10. 当前不做

- 多 worker
- Redis
- PostgreSQL 迁移
- 真实用户认证
- APK 构建
