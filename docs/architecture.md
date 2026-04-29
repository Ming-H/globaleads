# GlobalLeads 技术架构文档

> 版本：v1.0
> 日期：2026-04-25

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                         用户浏览器                           │
│                  globaleads.devfoxai.cn                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vercel (React SPA)                        │
│                  前端静态资源 + CDN                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ API 请求 (/api/*)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   阿里云服务器                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Nginx (:80 / :443)                      │   │
│  │  globaleads.devfoxai.cn/api/* → FastAPI :8002       │   │
│  │  leadmine.devfoxai.cn/api/*   → FastAPI :8000       │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                               │
│  ┌──────────┐  ┌──────────┐  ┌───────┐  ┌───────────────┐  │
│  │ FastAPI   │  │ Celery   │  │ Redis │  │ PostgreSQL    │  │
│  │ Backend   │←→│ Worker   │  │       │  │               │  │
│  │ :8002     │  │          │  │ :6379 │  │ :5432         │  │
│  └──────────┘  └────┬─────┘  └───────┘  └───────────────┘  │
│                      │                                       │
│                      ├──→ Reddit API                         │
│                      ├──→ Bluesky API                        │
│                      ├──→ YouTube API                        │
│                      ├──→ Apollo.io API                      │
│                      ├──→ Google Maps API                    │
│                      └──→ Ollama / DeepSeek API              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 技术栈

### 2.1 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主语言 |
| FastAPI | 0.110+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM（async 模式） |
| asyncpg | - | PostgreSQL 异步驱动 |
| Celery | 5.x | 异步任务队列 |
| Redis | 7.x | 消息队列 + 缓存 |
| PostgreSQL | 16 | 主数据库 |
| httpx | - | 异步 HTTP 客户端（调用第三方 API） |
| python-jose | - | JWT 认证 |
| passlib | - | 密码加密 |

### 2.2 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Ant Design | 5.x | UI 组件库 |
| Ant Design Pro Components | - | 高级组件（ProTable 等） |
| Vite | 5.x | 构建工具 |
| Axios | - | HTTP 客户端 |
| ECharts | - | 数据可视化 |
| React Router DOM | 6.x | 路由 |

### 2.3 基础设施

| 技术 | 用途 |
|------|------|
| Docker + Docker Compose | 容器化部署 |
| GitHub 私有仓库 | 代码托管 |
| Vercel | 前端托管 |
| 阿里云 ECS | 后端服务器 |

---

## 3. 系统模块设计

### 3.1 后端模块

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口，lifespan 管理
│   ├── core/
│   │   ├── config.py            # 配置管理（环境变量）
│   │   ├── database.py          # 数据库连接
│   │   ├── security.py          # JWT + 密码工具
│   │   └── deps.py              # 依赖注入
│   ├── models/                  # SQLAlchemy 模型
│   │   ├── user.py
│   │   ├── social_task.py       # 社媒挖掘任务
│   │   ├── social_lead.py       # 社媒线索
│   │   ├── b2b_task.py          # B2B 搜索任务
│   │   ├── b2b_lead.py          # B2B 线索
│   │   └── base.py              # 基础模型 mixin
│   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── auth.py
│   │   ├── social_task.py
│   │   ├── social_lead.py
│   │   ├── b2b_task.py
│   │   └── b2b_lead.py
│   ├── api/v1/                  # API 路由
│   │   ├── auth.py              # 认证
│   │   ├── social_tasks.py      # 社媒任务 CRUD
│   │   ├── social_leads.py      # 社媒线索查询
│   │   ├── b2b_tasks.py         # B2B 任务 CRUD
│   │   ├── b2b_leads.py         # B2B 线索查询
│   │   └── dashboard.py         # 数据看板
│   ├── services/                # 业务逻辑
│   │   ├── reddit_service.py    # Reddit API 封装
│   │   ├── bluesky_service.py   # Bluesky API 封装
│   │   ├── youtube_service.py   # YouTube API 封装
│   │   ├── apollo_service.py    # Apollo API 封装
│   │   ├── google_maps_service.py
│   │   ├── hunter_service.py    # Hunter.io API 封装
│   │   └── ai_service.py        # LLM 分析（Ollama/DeepSeek）
│   ├── tasks/                   # Celery 异步任务
│   │   ├── social_crawl.py      # 社媒爬取任务
│   │   ├── b2b_search.py        # B2B 搜索任务
│   │   └── celery_app.py        # Celery 配置
│   └── utils/                   # 工具函数
├── requirements.txt
├── Dockerfile
└── .env.example
```

### 3.2 前端模块

```
frontend/
├── src/
│   ├── App.tsx                  # 路由配置
│   ├── main.tsx                 # 入口
│   ├── pages/
│   │   ├── Dashboard/           # 数据看板
│   │   ├── SocialTasks/         # 社媒任务管理
│   │   ├── SocialLeads/         # 社媒线索列表
│   │   ├── B2BTasks/            # B2B 任务管理
│   │   ├── B2BLeads/            # B2B 线索列表
│   │   ├── Login/               # 登录
│   │   └── Settings/            # 系统设置
│   ├── components/
│   │   ├── Layout/              # 布局（Header + Sidebar）
│   │   ├── TaskForm/            # 任务创建表单
│   │   ├── LeadTable/           # 线索表格
│   │   └── Charts/              # 图表组件
│   ├── hooks/                   # 自定义 Hooks
│   ├── services/                # API 调用封装
│   ├── types/                   # TypeScript 类型定义
│   └── utils/                   # 工具函数
├── package.json
├── vite.config.ts
├── tsconfig.json
└── Dockerfile
```

---

## 4. 核心业务流程

### 4.1 社媒线索挖掘流程

```
用户创建任务（关键词 + 平台）
        │
        ▼
  任务写入 DB（状态：pending）
        │
        ▼
  Celery Worker 取任务
        │
        ▼
  调用社媒 API 搜索（Reddit/Bluesky/YouTube）
        │
        ▼
  获取原始帖子/评论列表
        │
        ▼
  批量发送给 LLM 分析（Ollama/DeepSeek）
  - Prompt：分析该内容是否表达购买/求购意向
  - 输出：是否有意向 + 评分 + 标签
        │
        ▼
  筛选出有意向的内容
        │
        ▼
  写入 social_leads 表
        │
        ▼
  更新任务状态为 completed
```

### 4.2 B2B 客户搜索流程

```
用户创建任务（行业 + 地区 + 公司规模）
        │
        ▼
  任务写入 DB（状态：pending）
        │
        ▼
  Celery Worker 取任务
        │
        ▼
  调用 Apollo / Google Maps API 搜索公司
        │
        ▼
  获取公司列表 + 联系人
        │
        ▼
  调用 Hunter.io 获取邮箱
        │
        ▼
  邮箱验证（API 验证）
        │
        ▼
  写入 b2b_leads 表
        │
        ▼
  更新任务状态为 completed
```

---

## 5. 大模型切换设计

通过环境变量 `AI_PROVIDER` 控制，不改代码：

```python
# config.py
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")  # "ollama" 或 "deepseek"

if AI_PROVIDER == "ollama":
    AI_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    AI_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")
    AI_API_KEY = ""  # Ollama 无需 API Key
elif AI_PROVIDER == "deepseek":
    AI_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    AI_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    AI_API_KEY = os.getenv("DEEPSEEK_API_KEY")
```

统一使用 OpenAI 兼容接口格式，Ollama 和 DeepSeek 都支持。

---

## 6. API 额度管理

系统需跟踪各第三方 API 的使用量，避免超额：

| API | 月额度 | 系统跟踪 |
|-----|--------|---------|
| Reddit | 60 请求/分钟（限速） | 请求限速器 |
| Bluesky | 3000 请求/5 分钟（限速） | 请求限速器 |
| YouTube | 10,000 配额单位/天 | 每日配额计数 |
| Apollo | 900 积分/月 | 月度积分计数 |
| Google Maps | 6,250 次/月 | 月度请求计数 |
| Hunter.io | 25 积分/月 | 月度积分计数 |
| Hunter.io | 25 积分/月 | 月度积分计数 |

额度不足时任务标记为 `quota_exceeded`，提示用户。

---

## 7. 与 LeadMine 共用资源

GlobalLeads 部署在同一台阿里云服务器上，与 LeadMine 共用：

| 资源 | 共用方式 |
|------|---------|
| PostgreSQL | 同一个 PG 实例，不同数据库（`leadmine` / `globaleads`） |
| Redis | 同一个 Redis 实例，不同 DB 编号（DB 0 / DB 1） |
| Docker | 同一个 Docker 环境 |
| 服务器 | 同一台 ECS |

不共用的：
| 资源 | 独立 |
|------|------|
| FastAPI 进程 | 独立，不同端口（LeadMine :8000, GlobalLeads :8002） |
| Celery Worker | 独立，不同队列名 |
| 前端 | 独立部署在 Vercel |

---

## 8. 日志系统

### 8.1 架构

```
请求/任务 → Python logging → RotatingFileHandler → /app/logs/*.log
                                                    ↓
                                              Docker Volume 挂载
                                                    ↓
                                       /home/admin/globaleads/logs/
```

### 8.2 日志文件

| 文件 | 内容 | 轮转策略 | 磁盘上限 |
|------|------|---------|---------|
| `app.log` | 全部日志（INFO+），含 API 请求、认证、业务操作 | 20MB x 3 备份 | 60MB |
| `error.log` | 仅 ERROR 及以上 | 10MB x 2 备份 | 20MB |
| `task.log` | Celery 任务执行日志 | 20MB x 2 备份 | 40MB |
| **合计** | | | **120MB** |

### 8.3 日志格式

```
2026-04-25 10:30:15.123 [INFO] [request_id=abc123] api.access: POST /api/v1/auth/login 200 45ms user=admin
2026-04-25 10:30:20.456 [INFO] [task_id=5] task.social_crawl: 开始执行 - keywords=["LED"] platforms=["reddit"]
2026-04-25 10:31:05.789 [INFO] [task_id=5] task.social_crawl: 完成 - 获取 120 条原始内容, 筛选 12 条线索
2026-04-25 10:31:10.012 [WARNING] service.reddit: 接近速率限制 (55/60 req/min)
2026-04-25 10:32:00.345 [ERROR] [request_id=def456] service.ai_service: LLM 调用失败 - ConnectionTimeout(url=..., timeout=60s)
```

格式：`{时间} [{级别}] [{追踪ID}] {模块}: {消息} {上下文详情}`

### 8.4 追踪 ID

- **API 请求**：每个请求生成唯一 `request_id`（UUID 短码），贯穿请求全链路日志
- **Celery 任务**：使用 `task_id`（数据库任务 ID），贯穿任务执行全链路

### 8.5 记录规则

**必须记录：**
- 每个 API 请求（方法、路径、状态码、耗时、用户）
- 认证事件（登录成功/失败、Token 过期）
- 任务生命周期（开始、进度、完成、失败）
- 第三方 API 调用（平台、耗时、结果数量）
- AI 分析调用（模型、耗时、评分分布）
- 错误和异常（堆栈 + 上下文）

**禁止记录：**
- 密码、Token、API Key 等敏感信息
- 线索原始内容全文（仅记录数量和评分）
- 请求/响应体中的大段文本

### 8.6 模块结构

```
app/core/logging.py       # 日志配置（格式、Handler、轮转）
app/middleware/logging.py  # FastAPI 请求日志中间件（自动注入 request_id）
```

### 8.7 运维命令

```bash
# 查看实时日志
tail -f /home/admin/globaleads/logs/app.log

# 查看错误
grep ERROR /home/admin/globaleads/logs/error.log | tail -20

# 按追踪 ID 查询完整请求链路
grep "request_id=abc123" /home/admin/globaleads/logs/app.log

# 按任务 ID 查询任务执行过程
grep "task_id=5" /home/admin/globaleads/logs/task.log

# Docker 容器日志（stdout 镜像）
docker logs -f globaleads-backend --tail 100
```
