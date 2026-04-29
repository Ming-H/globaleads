# GlobalLeads 部署检查清单

> 首次部署时按顺序执行，每完成一项打勾

---

## 一、阿里云服务器 — 后端

### 1. 数据库准备
- [ ] 进入已有的 PostgreSQL 容器：`docker exec -it <postgres容器> psql -U leadmine`
- [ ] 创建数据库：`CREATE DATABASE globaleads;`
- [ ] 验证：`\l` 确认 globaleads 库已创建

### 2. 代码部署
- [ ] `cd /home/admin && git clone git@github.com:<username>/globaleads.git`
- [ ] `cd globaleads`
- [ ] `cp backend/.env.example backend/.env && vim backend/.env`
- [ ] 确认 .env 中以下配置正确：
  - [ ] `DATABASE_URL=postgresql+asyncpg://leadmine:<密码>@<PG容器>:5432/globaleads`
  - [ ] `REDIS_URL=redis://<Redis容器>:6379/1`
  - [ ] `AI_PROVIDER=ollama` 或 `deepseek`
  - [ ] `PORT=8002`
  - [ ] 各 API Key 已填写

### 3. Docker 启动
- [ ] `docker compose -f docker-compose.server.yml up -d --build`
- [ ] `docker ps` 确认 globaleads-backend 和 globaleads-celery 在运行
- [ ] `docker logs globaleads-backend --tail 20` 检查启动日志无报错
- [ ] `curl http://localhost:8002/api/health` 返回 `{"status":"ok"}`

### 4. Nginx 配置
- [ ] 添加 GlobalLeads 反向代理到 `/etc/nginx/conf.d/devfoxai.conf`：
  ```nginx
  server {
      listen 80;
      server_name globaleads.devfoxai.cn;
      location /api/ {
          proxy_pass http://127.0.0.1:8002;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```
- [ ] `sudo nginx -t` 检查配置
- [ ] `sudo nginx -s reload` 重载

### 5. SSL 证书
- [ ] `sudo certbot --nginx -d globaleads.devfoxai.cn`
- [ ] 验证 HTTPS 访问正常

### 6. 监控告警
- [ ] `cp deploy/.env.example deploy/.env`
- [ ] 在飞书群添加自定义机器人，复制 Webhook URL
- [ ] `vim deploy/.env` 填入 `FEISHU_WEBHOOK_URL=...`
- [ ] 手动测试：`bash deploy/monitor.sh`，确认飞书收到消息
- [ ] 添加 crontab：`crontab -e`，加入：
  ```
  */5 * * * * /home/admin/globaleads/deploy/monitor.sh >> /home/admin/globaleads/logs/monitor.log 2>&1
  ```

---

## 二、DNS 配置（阿里云域名解析）

- [ ] 添加 A 记录：主机记录 `globaleads`，记录值 `<服务器公网IP>`
- [ ] 验证：`ping globaleads.devfoxai.cn` 解析到正确 IP

---

## 三、Vercel — 前端

### 1. 创建项目
- [ ] Vercel → Add New Project → 导入 GitHub `globaleads` 仓库
- [ ] Framework Preset: Vite
- [ ] Root Directory: `frontend`
- [ ] Build Command: `npm run build`
- [ ] Output Directory: `dist`

### 2. 环境变量
- [ ] 添加 `VITE_API_BASE_URL=https://globaleads.devfoxai.cn/api/v1`

### 3. 域名绑定
- [ ] Vercel 项目 Settings → Domains → 添加 `globaleads.devfoxai.cn`
- [ ] 验证 CNAME 记录：主机记录 `globaleads`，记录值 `cname.vercel-dns.com`

---

## 四、验证

- [ ] 访问 `https://globaleads.devfoxai.cn` 页面正常加载
- [ ] 登录 admin / admin123 成功
- [ ] 创建社媒任务，确认 Celery worker 执行
- [ ] 查看 Dashboard 数据正常
- [ ] 导出 CSV / Excel 功能正常
- [ ] 系统设置页查看 API 用量正常

---

## 五、日常运维命令速查

```bash
# 更新后端
cd /home/admin/globaleads && git pull origin main
docker compose -f docker-compose.server.yml restart backend celery

# 查看日志
tail -f /home/admin/globaleads/logs/app.log

# 查看容器状态
docker stats --no-stream

# 数据库备份
docker exec <postgres容器> pg_dump -U leadmine globaleads > backup_$(date +%Y%m%d).sql
```
