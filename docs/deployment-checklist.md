# GlobalLeads 部署检查清单

> 首次部署时按顺序执行，每完成一项打勾。最后更新：2026-04-29

---

## 一、阿里云服务器 — 后端部署

### 1. 数据库准备
- [ ] 进入已有的 PostgreSQL 容器：`docker exec -it <postgres容器> psql -U globaleads`
- [ ] 创建数据库：`CREATE DATABASE globaleads;`
- [ ] 验证：`\l` 确认 globaleads 库已创建
- [ ] 退出：`\q`

### 2. 代码部署
- [ ] `cd /home/admin`
- [ ] 克隆仓库：`git clone git@github.com:<username>/globaleads.git`
- [ ] 进入目录：`cd globaleads`
- [ ] 复制环境变量：`cp backend/.env.example backend/.env`
- [ ] 编辑配置：`vim backend/.env`

**确认 .env 中以下配置正确：**
```bash
# 数据库（连接到 LeadMine 的 PostgreSQL）
DATABASE_URL=postgresql+asyncpg://globaleads:your_password@postgres:5432/globaleads

# Redis（连接到 LeadMine 的 Redis）
REDIS_URL=redis://redis:6379/1

# AI Provider
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:0.6b

# Celery
CELERY_BROKER_URL=redis://redis:6379/1

# 服务端口
PORT=8002

# JWT（生成强随机密钥）
JWT_SECRET=<生成一个强随机字符串>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=72

# CORS（允许前端域名）
CORS_ORIGINS=https://your-domain.example.com

# API Keys（根据实际使用填写）
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
BLUESKY_HANDLE=
BLUESKY_PASSWORD=
YOUTUBE_API_KEY=
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_CX=
```

### 3. Docker 启动
- [ ] 确认 应用网络存在：`docker network ls | grep globaleads`
- [ ] 构建并启动：`docker compose -f docker-compose.server.yml up -d --build`
- [ ] 检查容器状态：`docker ps | grep globaleads`
- [ ] 确认以下容器在运行：
  - [ ] `globaleads-backend`
  - [ ] `globaleads-celery`
- [ ] 查看后端日志：`docker logs globaleads-backend --tail 50`
- [ ] 查看 Celery 日志：`docker logs globaleads-celery --tail 50`
- [ ] 健康检查：`curl http://localhost:8002/api/health`
  - 预期返回：`{"status":"ok","version":"1.0.0","checks":{"database":"ok","redis":"ok"}}`

### 4. Nginx 配置
- [ ] 编辑 Nginx 配置：`sudo vim /etc/nginx/conf.d/example.conf`
- [ ] 添加 GlobalLeads 反向代理：
```nginx
# GlobalLeads API
server {
    listen 80;
    server_name your-domain.example.com;

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```
- [ ] 检查配置：`sudo nginx -t`
- [ ] 重载 Nginx：`sudo nginx -s reload`

### 5. SSL 证书配置
- [ ] 申请证书：`sudo certbot --nginx -d your-domain.example.com`
- [ ] 验证 HTTPS：`curl https://your-domain.example.com/api/health`
- [ ] 确认证书自动续期：`sudo certbot renew --dry-run`

### 6. 日志目录
- [ ] 创建日志目录：`mkdir -p /opt/globaleads/logs`
- [ ] 设置权限：`chmod 755 /opt/globaleads/logs`

### 7. 监控告警设置
- [ ] 复制监控配置：`cp deploy/.env.example deploy/.env`
- [ ] 创建飞书机器人，获取 Webhook URL
- [ ] 编辑监控配置：`vim deploy/.env`
  ```bash
  FEISHU_WEBHOOK_URL=<飞书机器人 Webhook URL>
  ```
- [ ] 手动测试监控：`bash deploy/monitor.sh`
- [ ] 确认飞书群收到测试消息
- [ ] 添加定时任务：`crontab -e`
  ```bash
  */5 * * * * /opt/globaleads/deploy/monitor.sh >> /opt/globaleads/logs/monitor.log 2>&1
  ```

### 8. Ollama 服务验证
- [ ] 确认 Ollama 已安装：`ollama --version`
- [ ] 确认模型已下载：`ollama list | grep qwen3`
- [ ] 测试 AI 服务：`curl http://localhost:11434/api/generate -d '{"model":"qwen3:0.6b","prompt":"test"}'`

---

## 二、DNS 配置（阿里云域名解析）

- [ ] 登录阿里云域名控制台
- [ ] 找到 `example.com` 域名
- [ ] 添加 A 记录：
  - 主机记录：`globaleads`
  - 记录类型：`A`
  - 记录值：`<服务器公网IP>`
  - TTL：`600`
- [ ] 验证解析：`ping your-domain.example.com`
- [ ] 确认解析到正确的服务器 IP

---

## 三、Vercel — 前端部署

### 1. 项目连接
- [ ] 登录 [Vercel Dashboard](https://vercel.com/dashboard)
- [ ] 点击 "Add New Project"
- [ ] 导入 GitHub 仓库：选择 `globaleads`
- [ ] 配置项目：
  - **Framework Preset**: `Vite`
  - **Root Directory**: `frontend`
  - **Build Command**: `npm run build`
  - **Output Directory**: `dist`
  - **Install Command**: `npm install`

### 2. 环境变量配置
- [ ] 进入项目 Settings → Environment Variables
- [ ] 添加以下变量：
  ```bash
  # 生产环境 API 地址
  VITE_API_BASE_URL=https://your-domain.example.com/api/v1
  ```
- [ ] 选择环境：`Production` / `Preview` / `Development`
- [ ] 保存并重新部署

### 3. 域名绑定
- [ ] 进入项目 Settings → Domains
- [ ] 添加域名：`your-domain.example.com`
- [ ] Vercel 会提供 CNAME 配置：
  - 主机记录：`globaleads`
  - 记录类型：`CNAME`
  - 记录值：`cname.vercel-dns.com`
- [ ] 在阿里云 DNS 中添加上述 CNAME 记录
- [ ] 等待 DNS 生效（通常 5-30 分钟）
- [ ] Vercel 显示域名状态为 "Valid Configuration"

### 4. 部署验证
- [ ] 查看 Deployments 页面，确认最新构建成功
- [ ] 点击部署日志，确认无错误

---

## 四、完整功能验证

### 1. 页面访问
- [ ] 访问：`https://your-domain.example.com`
- [ ] 确认页面正常加载，无 404 错误
- [ ] 打开浏览器控制台，确认无 API 请求失败

### 2. 用户认证
- [ ] 使用默认账号登录：`admin` / `changeme`
- [ ] 确认登录成功，跳转到 Dashboard
- [ ] 退出登录，确认跳转到登录页

### 3. 社媒任务功能
- [ ] 创建社媒任务：
  - 名称：`测试任务`
  - 关键词：`LED`
  - 平台：`Reddit`
- [ ] 确认任务状态变为 `running`
- [ ] 等待 30 秒，刷新页面，查看任务状态
- [ ] 确认 Celery worker 正常处理（查看日志）
- [ ] 如有线索生成，查看社媒线索列表

### 4. B2B 任务功能
- [ ] 创建 B2B 任务：
  - 名称：`B2B 测试`
  - 行业：`Lighting`
  - 数据源：`Google Search`、`OpenStreetMap`
- [ ] 确认任务创建成功
- [ ] 查看任务状态更新

### 5. Dashboard 统计
- [ ] 访问 Dashboard 页面
- [ ] 确认统计数据正确显示
- [ ] 确认趋势图正常加载

### 6. 导出功能
- [ ] 在社媒线索列表，点击"导出 CSV"
- [ ] 确认文件下载成功
- [ ] 打开 CSV 文件，确认数据完整
- [ ] 测试 Excel 导出（如果有线索）

### 7. 系统设置
- [ ] 访问设置页面
- [ ] 确认 API 用量显示正常
- [ ] 确认 Redis 连接正常

---

## 五、日常运维命令速查

### 更新代码
```bash
# 拉取最新代码
cd /opt/globaleads
git pull origin main

# 重启服务
docker compose -f docker-compose.server.yml restart backend celery

# 如果需要重新构建
docker compose -f docker-compose.server.yml up -d --build
```

### 查看日志
```bash
# 应用日志（通过 Docker）
docker logs globaleads-backend --tail 100 -f
docker logs globaleads-celery --tail 100 -f

# 文件日志（如果配置了文件输出）
tail -f /opt/globaleads/logs/app.log
tail -f /opt/globaleads/logs/celery.log

# 监控日志
tail -f /opt/globaleads/logs/monitor.log
```

### 容器管理
```bash
# 查看容器状态
docker ps | grep globaleads

# 查看资源占用
docker stats globaleads-backend globaleads-celery

# 进入容器
docker exec -it globaleads-backend bash
docker exec -it globaleads-celery bash

# 重启单个容器
docker restart globaleads-backend
docker restart globaleads-celery
```

### 数据库操作
```bash
# 进入数据库
docker exec -it postgres psql -U globaleads -d globaleads

# 数据库备份
docker exec postgres pg_dump -U globaleads globaleads > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker exec -i postgres psql -U globaleads globaleads < backup_20260429.sql
```

### Redis 操作
```bash
# 进入 Redis
docker exec -it redis redis-cli

# 查看所有 key
KEYS *

# 清空 GlobalLeads 相关缓存
FLUSHDB
```

---

## 六、故障排查

### 后端无法启动
1. 检查日志：`docker logs globaleads-backend`
2. 常见原因：
   - 数据库连接失败 → 检查 DATABASE_URL
   - Redis 连接失败 → 检查 REDIS_URL
   - 端口占用 → `netstat -tlnp | grep 8002`
   - 环境变量错误 → 检查 .env 文件

### Celery 任务不执行
1. 检查 Celery 状态：`docker logs globaleads-celery`
2. 进入容器检查队列：`docker exec -it globaleads-celery celery -A app.tasks.celery_app inspect active`
3. 常见原因：
   - Redis 连接失败
   - 任务未正确注册
   - 并发数配置问题

### 前端 API 请求失败
1. 检查浏览器控制台网络请求
2. 确认 API 地址正确：`https://your-domain.example.com/api/v1`
3. 检查 CORS 配置
4. 检查 Nginx 代理配置

### AI 分析不工作
1. 确认 Ollama 运行：`curl http://localhost:11434/api/tags`
2. 检查模型已下载：`ollama list`
3. 确认配置：OLLAMA_BASE_URL 和 OLLAMA_MODEL
4. 测试 API：`curl http://localhost:11434/api/generate -d '{"model":"qwen3:0.6b","prompt":"test"}'`

---

## 七、安全检查清单

- [ ] 修改默认管理员密码
- [ ] JWT_SECRET 使用强随机字符串
- [ ] 数据库密码使用强密码
- [ ] API Keys 不提交到 Git
- [ ] .env 文件已添加到 .gitignore
- [ ] Nginx 配置安全头
- [ ] SSL 证书有效且自动续期
- [ ] 防火墙只开放必要端口（80, 443, 22）
- [ ] 定期备份数据库
- [ ] 监控告警正常工作

---

## 八、性能优化建议

- [ ] 配置 PostgreSQL 连接池
- [ ] 配置 Redis 持久化
- [ ] 启用 Nginx gzip 压缩
- [ ] 配置 CDN 加速静态资源
- [ ] 设置适当的日志轮转
- [ ] 监控容器资源使用
- [ ] 定期清理旧日志文件

---

## 九、更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-29 | v1.1 | 完善监控、故障排查、安全检查 |
| 2026-04-25 | v1.0 | 初始版本 |
