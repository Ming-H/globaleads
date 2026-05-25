# GlobalLeads 部署检查清单

本文档提供完整的部署检查清单，涵盖服务器端和 Vercel 端的所有步骤。

---

## 前置准备

### 1. 服务器环境检查

- [ ] **服务器规格**
  - [ ] CPU: 至少 2 核心
  - [ ] 内存: 至少 4GB（推荐 8GB）
  - [ ] 磁盘: 至少 20GB 可用空间
  - [ ] 操作系统: Ubuntu 20.04+ / CentOS 7+ / Debian 10+

- [ ] **软件依赖**
  - [ ] Docker 20.10+
  - [ ] Docker Compose 2.0+
  - [ ] Git
  - [ ] Nginx（可选，用于反向代理）

- [ ] **验证安装**
  ```bash
  docker --version
  docker-compose --version
  git --version
  ```

### 2. 网络配置

- [ ] **端口开放**
  - [ ] 8002: Backend API 服务
  - [ ] 80/443: HTTP/HTTPS（如使用 Nginx）
  
- [ ] **防火墙规则**
  ```bash
  # Ubuntu UFW
  sudo ufw allow 8002/tcp
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  
  # CentOS firewalld
  sudo firewall-cmd --permanent --add-port=8002/tcp
  sudo firewall-cmd --permanent --add-port=80/tcp
  sudo firewall-cmd --permanent --add-port=443/tcp
  sudo firewall-cmd --reload
  ```

---

## 服务器端部署

### 3. 数据库准备

- [ ] **PostgreSQL 检查**
  - [ ] 确认 PostgreSQL 容器运行正常
    ```bash
    docker ps | grep postgres
    ```
  - [ ] 创建 `globaleads` 数据库
    ```bash
    docker exec -it leadmine-postgres psql -U leadmine -c "CREATE DATABASE globaleads;"
    ```
  - [ ] 验证数据库连接
    ```bash
    docker exec -it leadmine-postgres psql -U leadmine -d globaleads -c "SELECT version();"
    ```

- [ ] **Redis 检查**
  - [ ] 确认 Redis 容器运行正常
    ```bash
    docker ps | grep redis
    ```
  - [ ] 验证 Redis 连接
    ```bash
    docker exec -it leadmine-redis redis-cli -n 1 PING
    ```
    预期返回: `PONG`

### 4. 代码部署

- [ ] **拉取代码**
  ```bash
  cd /opt
  sudo git clone <repository-url> globaleads
  cd globaleads
  ```

- [ ] **配置环境变量**
  - [ ] 复制环境变量模板
    ```bash
    cp backend/.env.example backend/.env
    ```
  - [ ] 编辑 `backend/.env`，配置以下项：
    ```bash
    # 数据库连接（指向 leadmine 的 PostgreSQL）
    DATABASE_URL=postgresql+asyncpg://globaleads:your_password@postgres:5432/globaleads
    
    # Redis 连接（指向 leadmine 的 Redis，使用 DB 1）
    REDIS_URL=redis://redis:6379/1
    
    # CORS（配置 Vercel 域名）
    CORS_ORIGINS=https://your-domain.vercel.app,https://your-custom-domain.com
    
    # JWT 密钥（必须修改！）
    JWT_SECRET=<生成一个强随机字符串>
    
    # AI 提供商配置
    AI_PROVIDER=ollama  # 或 deepseek
    OLLAMA_BASE_URL=http://host.docker.internal:11434
    OLLAMA_MODEL=qwen3:0.6b
    
    # 第三方 API 密钥
    REDDIT_CLIENT_ID=<你的 Reddit Client ID>
    REDDIT_CLIENT_SECRET=<你的 Reddit Secret>
    BLUESKY_HANDLE=<你的 Bluesky 用户名>
    BLUESKY_PASSWORD=<你的 Bluesky 密码>
    YOUTUBE_API_KEY=<你的 YouTube API Key>
    GOOGLE_SEARCH_API_KEY=<你的 Google Custom Search API Key>
    GOOGLE_SEARCH_CX=<你的 Google Custom Search Engine ID>
    
    # Celery 配置
    CELERY_BROKER_URL=redis://redis:6379/1
    ```
  - [ ] 设置文件权限
    ```bash
    chmod 600 backend/.env
    ```

- [ ] **检查共享网络**
  - [ ] 确认 `leadmine_default` 网络存在
    ```bash
    docker network ls | grep leadmine_default
    ```
  - [ ] 如不存在，创建网络
    ```bash
    docker network create leadmine_default
    ```

### 5. 构建和启动

- [ ] **创建日志目录**
  ```bash
  mkdir -p /opt/globaleads/logs
  chmod 755 /opt/globaleads/logs
  ```

- [ ] **构建 Docker 镜像**
  ```bash
  cd /opt/globaleads
  docker compose -f docker-compose.server.yml build
  ```
  预期输出：镜像构建成功，无错误

- [ ] **启动服务**
  ```bash
  docker compose -f docker-compose.server.yml up -d
  ```

- [ ] **验证容器状态**
  ```bash
  docker ps | grep globaleads
  ```
  应该看到两个容器：
  - `globaleads-backend` (端口 8002)
  - `globaleads-celery` (Worker 进程)

- [ ] **查看启动日志**
  ```bash
  # Backend 日志
  docker logs -f globaleads-backend
  
  # Celery 日志
  docker logs -f globaleads-celery
  ```
  预期看到服务启动成功消息

### 6. 健康检查

- [ ] **API 健康检查**
  ```bash
  curl http://localhost:8002/api/health
  ```
  预期返回：
  ```json
  {
    "status": "ok",
    "version": "1.0.0",
    "checks": {
      "database": "ok",
      "redis": "ok"
    }
  }
  ```

- [ ] **数据库表初始化**
  - [ ] 检查表是否已创建
    ```bash
    docker exec -it leadmine-postgres psql -U leadmine -d globaleads -c "\dt"
    ```
  - [ ] 应该看到以下表：
    - `users`
    - `social_tasks`
    - `social_leads`
    - `b2b_tasks`
    - `b2b_leads`

- [ ] **默认管理员账号**
  - [ ] 使用默认账号登录测试
    ```bash
    curl -X POST http://localhost:8002/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username":"admin","password":"admin123"}'
    ```
  - [ ] **重要**: 首次登录后立即修改密码！

### 7. 监控配置

- [ ] **配置监控告警**
  - [ ] 复制监控配置
    ```bash
    cp deploy/.env.example deploy/.env
    ```
  - [ ] 编辑 `deploy/.env`，配置飞书 Webhook
    ```bash
    FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url
    ```
  - [ ] 设置监控脚本权限
    ```bash
    chmod +x deploy/monitor.sh
    ```
  - [ ] 添加到 crontab
    ```bash
    crontab -e
    ```
    添加以下行：
    ```cron
    */5 * * * * cd /opt/globaleads && ./deploy/monitor.sh
    ```

- [ ] **测试监控脚本**
  ```bash
  ./deploy/monitor.sh
  ```
  预期返回状态码 0（正常）

---

## Vercel 端部署

### 8. Vercel 项目配置

- [ ] **安装 Vercel CLI**
  ```bash
  npm install -g vercel
  ```

- [ ] **登录 Vercel**
  ```bash
  vercel login
  ```
  按提示完成浏览器授权

- [ ] **部署前端**
  ```bash
  cd /opt/globaleads/frontend
  vercel
  ```
  按提示操作：
  - [ ] Set up and deploy: `Y`
  - [ ] Which scope: 选择你的账号
  - [ ] Link to existing project: `N`
  - [ ] Project name: `globaleads-frontend` (或自定义)
  - [ ] In which directory: `.`
  - [ ] Want to override settings: `N`

- [ ] **记录部署 URL**
  - [ ] Vercel 会提供部署 URL: `https://globaleads-frontend-xxx.vercel.app`
  - [ ] 保存此 URL 用于后续配置

### 9. 环境变量配置

- [ ] **在 Vercel Dashboard 中配置**
  - [ ] 登录 Vercel Dashboard: https://vercel.com/dashboard
  - [ ] 选择 `globaleads-frontend` 项目
  - [ ] 进入 Settings → Environment Variables
  - [ ] 添加以下变量：
    ```
    Name: VITE_API_BASE_URL
    Value: https://your-backend-domain.com
    Environment: Production, Preview, Development
    ```

- [ ] **重新部署以应用环境变量**
  ```bash
  vercel --prod
  ```

### 10. 自定义域名（可选）

- [ ] **添加域名**
  - [ ] Vercel Dashboard → Settings → Domains
  - [ ] 点击 "Add" 添加你的自定义域名
  - [ ] 选择域名类型（主域名或子域名）

- [ ] **配置 DNS**
  - [ ] 根据提示在域名注册商处添加 DNS 记录
  - [ ] A 记录或 CNAME 记录
  - [ ] 等待 DNS 生效（通常 5-30 分钟）

- [ ] **验证 DNS**
  ```bash
  dig your-custom-domain.com
  ```
  预期看到指向 Vercel 的解析记录

- [ ] **配置 HTTPS**
  - [ ] Vercel 自动为自定义域名提供 SSL 证书
  - [ ] 等待证书自动签发

### 11. 验证前端部署

- [ ] **访问部署的 URL**
  - [ ] 检查页面是否正常加载
  - [ ] 打开浏览器控制台 (F12)
  - [ ] 检查是否有 JavaScript 错误

- [ ] **测试登录功能**
  - [ ] 进入登录页面
  - [ ] 使用 `admin` / `admin123` 登录
  - [ ] 检查是否成功跳转到首页

- [ ] **测试 API 调用**
  - [ ] 创建一个社媒任务
  - [ ] 检查任务是否成功提交
  - [ ] 刷新页面，查看任务是否显示

- [ ] **测试各页面**
  - [ ] Dashboard（数据看板）
  - [ ] Social Tasks（社媒任务）
  - [ ] Social Leads（社媒线索）
  - [ ] B2B Tasks（B2B 任务）
  - [ ] B2B Leads（B2B 线索）
  - [ ] Settings（设置）

---

## 安全配置

### 12. 安全加固

- [ ] **修改默认密码**
  - [ ] 首次登录后立即修改管理员密码
  - [ ] 或通过 API 修改

- [ ] **HTTPS 配置（使用 Nginx）**
  - [ ] 安装 Nginx
    ```bash
    sudo apt install nginx certbot python3-certbot-nginx
    ```
  - [ ] 配置 Nginx 反向代理
    ```nginx
    server {
        listen 443 ssl http2;
        server_name your-domain.com;
        
        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
        
        # Backend API
        location /api/ {
            proxy_pass http://localhost:8002;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Frontend (Vercel)
        location / {
            proxy_pass https://your-vercel-app.vercel.app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    
    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }
    ```
  - [ ] 获取 SSL 证书
    ```bash
    sudo certbot --nginx -d your-domain.com
    ```

- [ ] **API 密钥管理**
  - [ ] 所有 API 密钥存储在 `.env` 文件中
  - [ ] 确保 `.env` 文件权限正确 (`chmod 600`)
  - [ ] 不要将 `.env` 提交到版本控制
  - [ ] 定期轮换 API 密钥

### 13. 备份策略

- [ ] **数据库备份**
  - [ ] 创建备份目录
    ```bash
    mkdir -p /backup/globaleads
    ```
  - [ ] 设置定期备份脚本
    ```bash
    # 创建备份脚本
    cat > /backup/backup_globaleads.sh << 'EOF'
    #!/bin/bash
    BACKUP_DIR="/backup/globaleads"
    DATE=$(date +%Y%m%d_%H%M%S)
    docker exec leadmine-postgres pg_dump -U leadmine globaleads | gzip > $BACKUP_DIR/globaleads_$DATE.sql.gz
    # 保留最近 7 天的备份
    find $BACKUP_DIR -name "globaleads_*.sql.gz" -mtime +7 -delete
    EOF
    chmod +x /backup/backup_globaleads.sh
    ```
  - [ ] 添加到 crontab（每日凌晨 2 点）
    ```bash
    crontab -e
    ```
    添加：
    ```cron
    0 2 * * * /backup/backup_globaleads.sh
    ```

- [ ] **日志备份**
  - [ ] Docker 日志已配置轮转（max 3 个文件，每个 20MB）
  - [ ] 可选：配置集中日志收集

---

## 性能优化

### 14. 性能配置

- [ ] **数据库优化**
  - [ ] 为常用查询字段添加索引
  - [ ] 定期执行 VACUUM ANALYZE
    ```bash
    docker exec leadmine-postgres psql -U leadmine -d globaleads -c "VACUUM ANALYZE;"
    ```

- [ ] **资源限制检查**
  - [ ] 当前配置：
    - Backend: 256MB 内存 + 320MB swap
    - Celery: 256MB 内存 + 320MB swap
    - Celery 并发: 1
  - [ ] 根据实际负载调整参数
  - [ ] 监控容器资源使用
    ```bash
    docker stats
    ```

- [ ] **Celery 并发调整**
  - [ ] 当前并发数: 1
  - [ ] 如需更高吞吐量，可增加到 2-4
    ```yaml
    # 修改 docker-compose.server.yml
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 -Q globaleads
    ```

---

## 故障排查

### 常见问题及解决方案

- [ ] **容器无法启动**
  ```bash
  # 查看详细日志
  docker compose -f docker-compose.server.yml logs backend
  docker compose -f docker-compose.server.yml logs celery
  
  # 检查配置
  docker compose -f docker-compose.server.yml config
  ```

- [ ] **数据库连接失败**
  - [ ] 检查 `DATABASE_URL` 配置
  - [ ] 检查 PostgreSQL 容器状态
    ```bash
    docker ps | grep postgres
    ```
  - [ ] 测试数据库连接
    ```bash
    docker exec -it leadmine-postgres psql -U leadmine -d globaleads
  ```
  - [ ] 检查网络连接
    ```bash
    docker network inspect leadmine_default
    ```

- [ ] **Celery 任务不执行**
  - [ ] 检查 Celery 日志
    ```bash
    docker logs -f globaleads-celery
    ```
  - [ ] 验证 Redis 连接
    ```bash
    docker exec -it leadmine-redis redis-cli -n 1 PING
    ```
  - [ ] 检查队列名称是否匹配 (`globaleads`)
  - [ ] 测试 Celery worker
    ```bash
    docker exec globaleads-celery celery -A app.tasks.celery_app inspect active
    ```

- [ ] **Ollama 连接失败**
  - [ ] 检查 `OLLAMA_BASE_URL` 配置
  - [ ] 确认 Ollama 服务运行在宿主机
    ```bash
    curl http://localhost:11434/api/tags
    ```
  - [ ] 检查 `extra_hosts` 配置
  - [ ] 测试从容器内访问
    ```bash
    docker exec globaleads-backend curl http://host.docker.internal:11434/api/tags
    ```

- [ ] **前端无法连接 API**
  - [ ] 检查 `VITE_API_BASE_URL` 配置
  - [ ] 检查 CORS 配置
  - [ ] 查看浏览器控制台错误
  - [ ] 测试 API 直接访问
    ```bash
    curl https://your-api-domain.com/api/health
    ```

---

## 部署后验证

### 最终检查清单

- [ ] **服务器端**
  - [ ] Backend API 响应正常
  - [ ] Celery Worker 运行正常
  - [ ] 数据库表已创建
  - [ ] 默认管理员可登录
  - [ ] 日志文件正常写入
  - [ ] 监控告警已配置
  - [ ] 健康检查端点正常

- [ ] **前端**
  - [ ] Vercel 部署成功
  - [ ] 页面加载正常
  - [ ] API 调用正常
  - [ ] 登录功能正常
  - [ ] 各页面功能正常

- [ ] **集成测试**
  - [ ] 创建社媒任务 → 检查是否执行
  - [ ] 创建 B2B 任务 → 检查是否执行
  - [ ] 查看线索列表 → 检查数据展示
  - [ ] 导出功能 → 检查文件生成
  - [ ] 数据看板 → 检查统计数据

---

## 回滚计划

如部署失败，按以下步骤回滚：

```bash
# 1. 停止服务
cd /opt/globaleads
docker compose -f docker-compose.server.yml down

# 2. 恢复之前版本的代码
git checkout <previous-tag-or-commit>

# 3. 重新构建和启动
docker compose -f docker-compose.server.yml up -d --build

# 4. 等待服务启动
sleep 15

# 5. 验证服务
curl http://localhost:8002/api/health

# 6. 如需回滚数据库
docker exec -i leadmine-postgres psql -U leadmine globaleads < /backup/globaleads_backup.sql
```

---

## 附录

### A. 快速部署脚本

```bash
#!/bin/bash
set -e

echo "=== GlobalLeads 快速部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未安装 Docker Compose"
    exit 1
fi

# 拉取最新代码
echo "拉取最新代码..."
git pull origin main

# 构建镜像
echo "构建 Docker 镜像..."
docker compose -f docker-compose.server.yml build

# 启动服务
echo "启动服务..."
docker compose -f docker-compose.server.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 健康检查
echo "执行健康检查..."
curl -f http://localhost:8002/api/health || exit 1

echo "=== 部署完成 ==="
```

### B. 监控脚本状态码

监控脚本会返回以下状态码：
- `0`: 正常
- `1`: 警告（发送飞书通知）
- `2`: 严重（发送飞书通知）

### C. 有用的命令

```bash
# 查看所有容器状态
docker ps

# 查看容器资源使用
docker stats

# 进入容器
docker exec -it globaleads-backend bash

# 查看 Docker 日志
docker logs --tail 100 globaleads-backend

# 重启服务
docker compose -f docker-compose.server.yml restart

# 停止服务
docker compose -f docker-compose.server.yml down

# 完全重新部署
docker compose -f docker-compose.server.yml up -d --build --force-recreate
```

### D. 联系方式

如有问题，请联系：
- 技术支持: [your-email@example.com]
- 飞书群: [your-feishu-group]
- 文档: [docs-link]

---

**文档版本**: 1.0  
**最后更新**: 2026-04-29  
**维护者**: GlobalLeads Team
