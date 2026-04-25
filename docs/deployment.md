# GlobalLeads 部署运维文档

> 版本：v1.0
> 日期：2026-04-25

---

## 1. 部署架构

```
┌───────────────────────────────────────────────────────┐
│                   阿里云 ECS 服务器                     │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Nginx (:80 / :443)                  │  │
│  │                                                 │  │
│  │  leadmine.devfoxai.cn/api/*   → :8000           │  │
│  │  globaleads.devfoxai.cn/api/* → :8001           │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                             │
│  ┌──────────────┐  ┌───┴──────────┐                  │
│  │  LeadMine    │  │ GlobalLeads  │                  │
│  │  :8000       │  │  :8001       │                  │
│  │  (已有)       │  │  (新增)       │                  │
│  └──────────────┘  └──────────────┘                  │
│                                                      │
│  ┌──────────┐  ┌───────┐  ┌──────────────┐          │
│  │ Celery x2│  │ Redis │  │ PostgreSQL   │          │
│  │ (各1个)   │  │ :6379 │  │ :5432        │          │
│  └──────────┘  └───────┘  └──────────────┘          │
│                     (共用)       (不同DB)              │
└──────────────────────────────────────────────────────┘
        │                              │
        │ 阿里云 DNS (A记录 → 服务器IP)  │
        ▼                              ▼
┌──────────────────┐  ┌──────────────────────┐
│ Vercel            │  │ Vercel               │
│ globaleads.       │  │ leadmine.            │
│ devfoxai.cn       │  │ devfoxai.cn          │
│ (前端 SPA)        │  │ (前端 SPA)           │
└──────────────────┘  └──────────────────────┘
```

### 请求路由

```
用户访问 globaleads.devfoxai.cn
        │
        ├── 页面请求 → Vercel CDN（前端静态资源）
        │
        └── /api/* 请求 → DNS A记录 → 阿里云 Nginx
                              │
                              ├── Host: globaleads.devfoxai.cn → :8001
                              └── Host: leadmine.devfoxai.cn   → :8000
```

---

## 2. 服务器资源分配

### 2.1 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| LeadMine Backend | 8000 | 已有 |
| GlobalLeads Backend | 8001 | 新增 |
| PostgreSQL | 5432 | 共用 |
| Redis | 6379 | 共用 |
| Ollama | 11434 | 已有 |

### 2.2 数据库隔离

| 项目 | PostgreSQL 数据库 | Redis DB |
|------|-------------------|----------|
| LeadMine | `leadmine` | DB 0 |
| GlobalLeads | `globaleads` | DB 1 |

### 2.3 内存预算

| 服务 | 预估内存 |
|------|---------|
| LeadMine Backend + Celery | ~500MB（已有） |
| PostgreSQL | ~150MB |
| Redis | ~50MB |
| GlobalLeads Backend | ~200MB |
| GlobalLeads Celery | ~150MB |
| Ollama | ~300MB |
| 系统 + 其他 | ~300MB |
| **总计** | **~1.65GB / 1.9GB** |

> 注意：内存紧张，需控制 Celery 并发数为 1，限制 worker 内存。

---

## 3. 部署步骤

### 3.1 服务器端 — 后端部署

#### Step 1：创建数据库

```bash
# SSH 到阿里云
ssh aliyun

# 进入已有的 PostgreSQL 容器
docker exec -it <postgres_container> psql -U leadmine

# 创建 globaleads 数据库
CREATE DATABASE globaleads;
\q
```

#### Step 2：拉取代码

```bash
# 在服务器上创建项目目录
cd /home/admin
git clone git@github.com:<username>/globaleads.git
cd globaleads
```

#### Step 3：配置环境变量

```bash
cp backend/.env.example backend/.env
vim backend/.env
```

**.env 配置：**
```env
# 数据库（共用 PG，不同数据库）
DATABASE_URL=postgresql+asyncpg://leadmine:<password>@localhost:5432/globaleads

# Redis（共用，不同 DB）
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/1

# AI 配置（测试阶段用 Ollama）
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:0.6b

# JWT
JWT_SECRET=<生成一个随机密钥>
JWT_EXPIRE_HOURS=72

# 第三方 API Keys
REDDIT_CLIENT_ID=<reddit_client_id>
REDDIT_CLIENT_SECRET=<reddit_client_secret>
REDDIT_USER_AGENT="GlobalLeads/1.0"
YOUTUBE_API_KEY=<youtube_api_key>
APOLLO_API_KEY=<apollo_api_key>
GOOGLE_MAPS_API_KEY=<google_maps_api_key>
HUNTER_API_KEY=<hunter_api_key>
SNOV_API_KEY=<snov_api_key>
SNOV_API_SECRET=<snov_api_secret>

# 服务端口
PORT=8001
```

#### Step 4：Docker Compose 启动

```bash
docker-compose -f docker-compose.server.yml up -d
```

> 注意：PostgreSQL 和 Redis 使用已有的容器，不重复启动。Docker Compose 中用 `external_links` 或 `network` 连接已有服务。

### 3.2 Vercel — 前端部署

#### Step 1：Vercel 创建项目

1. 登录 Vercel → Add New Project
2. 导入 GitHub 私有仓库 `globaleads`
3. 配置：
   - Framework Preset: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

#### Step 2：配置环境变量

在 Vercel 项目设置中添加：
```
VITE_API_BASE_URL=https://<服务器IP或域名>:8001/api/v1
```

#### Step 3：绑定域名

1. 在 Vercel 项目设置 → Domains
2. 添加 `globaleads.devfoxai.cn`
3. 在阿里云 DNS 添加 CNAME 记录：
   - 主机记录：`globaleads`
   - 记录类型：CNAME
   - 记录值：`cname.vercel-dns.com`

---

## 4. 日常运维

### 4.1 更新部署

```bash
# 后端更新
ssh aliyun
cd /home/admin/globaleads
git pull origin main
docker-compose -f docker-compose.server.yml restart backend celery

# 前端更新 — 自动
# git push 后 Vercel 自动构建部署
```

### 4.2 查看日志

日志文件存储在 `/home/admin/globaleads/logs/`，通过 Docker Volume 持久化。

#### 文件日志（推荐）

| 文件 | 内容 | 轮转策略 | 磁盘上限 |
|------|------|---------|---------|
| `app.log` | 全量日志（API 请求、认证、业务操作） | 20MB x 3 | 60MB |
| `error.log` | 仅 ERROR 及以上 | 10MB x 2 | 20MB |
| `task.log` | Celery 任务执行日志 | 20MB x 2 | 40MB |

```bash
# 实时查看应用日志
tail -f /home/admin/globaleads/logs/app.log

# 实时查看任务日志
tail -f /home/admin/globaleads/logs/task.log

# 查看最近错误
tail -20 /home/admin/globaleads/logs/error.log

# 按请求追踪 ID 查询完整链路
grep "request_id=abc123" /home/admin/globaleads/logs/app.log

# 按任务 ID 查询执行过程
grep "task_id=5" /home/admin/globaleads/logs/task.log

# 查看今天的认证事件
grep "auth" /home/admin/globaleads/logs/app.log | grep "$(date +%Y-%m-%d)"

# 查看所有 4xx/5xx 请求
grep -E " [45][0-9]{2} " /home/admin/globaleads/logs/app.log
```

#### Docker 容器日志（stdout 镜像）

```bash
# 实时查看
docker logs -f globaleads-backend
docker logs -f globaleads-celery

# 查看最近 100 行
docker logs --tail 100 globaleads-backend
```

### 4.3 数据库备份

```bash
# 备份 globaleads 数据库
docker exec <postgres_container> pg_dump -U leadmine globaleads > globaleads_backup_$(date +%Y%m%d).sql
```

建议设置 crontab 定期备份：
```bash
# 每天凌晨 3 点备份
0 3 * * * docker exec <postgres_container> pg_dump -U leadmine globaleads > /home/admin/backups/globaleads_$(date +\%Y\%m\%d).sql
```

### 4.4 监控

- **API 额度**：通过系统设置页面查看各 API 用量
- **任务状态**：通过 Dashboard 查看任务成功率
- **服务器资源**：`free -h` / `df -h` / `docker stats`

---

## 5. Nginx 配置

### 5.1 安装 Nginx（如未安装）

```bash
sudo yum install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 5.2 配置文件

```nginx
# /etc/nginx/conf.d/devfoxai.conf

# LeadMine 后端 API
server {
    listen 80;
    server_name leadmine.devfoxai.cn;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# GlobalLeads 后端 API
server {
    listen 80;
    server_name globaleads.devfoxai.cn;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 检查配置
sudo nginx -t

# 重载配置
sudo nginx -s reload
```

### 5.3 DNS 配置

在阿里云域名解析中添加 A 记录：

| 主机记录 | 记录类型 | 记录值 |
|---------|---------|--------|
| `leadmine` | A | 服务器公网 IP |
| `globaleads` | A | 服务器公网 IP |
| `www` | CNAME | cname.vercel-dns.com |

### 5.4 SSL / HTTPS（推荐使用 Let's Encrypt）

```bash
# 安装 certbot
sudo yum install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d leadmine.devfoxai.cn -d globaleads.devfoxai.cn

# 自动续期（certbot 会自动添加 crontab）
sudo certbot renew --dry-run
```

配置后 Nginx 会自动增加 443 端口的 SSL 配置，HTTP 自动跳转 HTTPS。

---

## 6. Vercel 前端 API 地址配置

使用 Nginx 反向代理后，前端的 API 地址使用域名而非 IP：

```
VITE_API_BASE_URL=https://globaleads.devfoxai.cn/api/v1
```

---

## 6. 回滚方案

```bash
# 回滚到上一个版本
cd /home/admin/globaleads
git log --oneline -5  # 查看最近提交
git checkout <commit_hash>
docker-compose -f docker-compose.server.yml up -d --build
```

前端回滚：Vercel 控制台 → Deployments → 选择历史版本 → Promote to Production
