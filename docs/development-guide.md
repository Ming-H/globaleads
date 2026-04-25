# GlobalLeads 开发规范

> 版本：v1.0
> 日期：2026-04-25

---

## 1. 项目结构

```
globaleads/                      # GitHub 私有仓库
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               # 核心配置
│   │   ├── models/             # 数据模型
│   │   ├── schemas/            # 请求/响应模型
│   │   ├── api/v1/             # API 路由
│   │   ├── services/           # 业务逻辑
│   │   ├── tasks/              # Celery 任务
│   │   ├── tests/              # 测试
│   │   └── utils/              # 工具函数
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── .env                    # 不提交 Git
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── services/           # API 调用
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── types/              # 类型定义
│   │   └── utils/              # 工具函数
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/                        # 项目文档
├── docker-compose.yml           # 开发环境
├── docker-compose.server.yml    # 生产环境
├── .gitignore
└── README.md
```

---

## 2. Git 规范

### 2.1 分支策略

| 分支 | 用途 |
|------|------|
| `main` | 生产分支，稳定代码 |
| `dev` | 开发分支，日常合并 |
| `feature/<name>` | 功能分支 |
| `fix/<name>` | 修复分支 |

### 2.2 Commit 格式

```
<type>: <subject>

# 示例
feat: 添加 Reddit API 搜索服务
fix: 修复 Celery 任务超时问题
docs: 更新 API 接口文档
refactor: 重构 AI 分析服务
test: 添加社媒任务接口测试
```

类型：`feat` / `fix` / `docs` / `refactor` / `test` / `chore`

### 2.3 .gitignore

```
# 环境变量
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node
node_modules/
dist/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml
```

---

## 3. 后端开发规范

### 3.1 代码风格

- Python 3.10+，使用 type hints
- 异步优先：所有数据库操作和外部 API 调用使用 async/await
- 遵循 PEP 8

### 3.2 API 路由规范

```python
# api/v1/social_tasks.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.schemas.social_task import SocialTaskCreate, SocialTaskResponse
from app.services.social_task_service import SocialTaskService

router = APIRouter()

@router.get("/social-tasks", response_model=list[SocialTaskResponse])
async def list_social_tasks(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取社媒挖掘任务列表"""
    service = SocialTaskService(db)
    return await service.list_tasks(user_id=current_user.id, page=page, page_size=page_size)
```

### 3.3 Service 层规范

业务逻辑放在 Service 层，不写在路由里：

```python
# services/reddit_service.py

class RedditService:
    """Reddit API 封装"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def search_posts(self, keyword: str, limit: int = 50) -> list[dict]:
        """搜索帖子"""
        ...

    async def get_post_comments(self, post_id: str) -> list[dict]:
        """获取帖子评论"""
        ...
```

### 3.4 AI 服务规范

统一使用 OpenAI 兼容接口格式：

```python
# services/ai_service.py

class AIService:
    """AI 分析服务（支持 Ollama / DeepSeek 切换）"""

    async def analyze_purchase_intent(
        self, content: str, keywords: list[str]
    ) -> dict:
        """
        分析内容是否有购买意向

        Returns:
            {"has_intent": bool, "score": int, "tags": list[str], "analysis": str}
        """
        prompt = self._build_intent_prompt(content, keywords)
        response = await self._call_llm(prompt)
        return self._parse_response(response)
```

### 3.5 Celery 任务规范

```python
# tasks/social_crawl.py

from app.tasks.celery_app import celery_app
from app.services.reddit_service import RedditService
from app.services.ai_service import AIService

@celery_app.task(bind=True, max_retries=3)
def crawl_social_media(self, task_id: int):
    """社媒爬取异步任务"""
    # 1. 获取任务配置
    # 2. 调用社媒 API 搜索
    # 3. AI 分析
    # 4. 保存线索
    # 5. 更新任务状态
    ...
```

---

## 4. 前端开发规范

### 4.1 代码风格

- TypeScript strict 模式
- 函数组件 + Hooks
- Ant Design 5.x 组件优先

### 4.2 API 调用规范

```typescript
// services/api.ts

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器 — 添加 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 — 处理 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

```typescript
// services/socialTaskService.ts

import api from './api';

export const socialTaskService = {
  getTasks: (params: { page: number; page_size: number; status?: string }) =>
    api.get('/social-tasks', { params }),

  createTask: (data: SocialTaskCreate) =>
    api.post('/social-tasks', data),

  getTask: (id: number) =>
    api.get(`/social-tasks/${id}`),

  stopTask: (id: number) =>
    api.post(`/social-tasks/${id}/stop`),

  retryTask: (id: number) =>
    api.post(`/social-tasks/${id}/retry`),
};
```

### 4.3 页面组件规范

```typescript
// pages/SocialLeads/index.tsx

import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';

interface SocialLead {
  id: number;
  platform: string;
  author_name: string;
  content: string;
  ai_score: number;
  ai_tags: string[];
  status: string;
}

const columns: ProColumns<SocialLead>[] = [
  { title: '平台', dataIndex: 'platform', width: 80 },
  { title: '作者', dataIndex: 'author_name', width: 120 },
  { title: '内容', dataIndex: 'content', ellipsis: true, search: false },
  { title: '意向评分', dataIndex: 'ai_score', width: 100, sorter: true },
  { title: '标签', dataIndex: 'ai_tags', width: 150, search: false },
  { title: '状态', dataIndex: 'status', width: 100 },
];

export default function SocialLeads() {
  return (
    <ProTable<SocialLead>
      columns={columns}
      request={async (params) => {
        const { data } = await socialLeadService.getLeads(params);
        return { data: data.items, total: data.total, success: true };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
    />
  );
}
```

---

## 5. 环境变量管理

### 5.1 后端环境变量

所有配置通过环境变量管理，不硬编码：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | 数据库连接 | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/1` |
| `AI_PROVIDER` | AI 提供商 | `ollama` / `deepseek` |
| `OLLAMA_BASE_URL` | Ollama 地址 | `http://localhost:11434` |
| `DEEPSEEK_API_KEY` | DeepSeek Key | `sk-xxx` |
| `JWT_SECRET` | JWT 密钥 | 随机字符串 |
| `REDDIT_CLIENT_ID` | Reddit 客户端 ID | - |
| `REDDIT_CLIENT_SECRET` | Reddit 客户端密钥 | - |
| `YOUTUBE_API_KEY` | YouTube API Key | - |
| `APOLLO_API_KEY` | Apollo API Key | - |
| `GOOGLE_MAPS_API_KEY` | Google Maps Key | - |
| `HUNTER_API_KEY` | Hunter.io Key | - |

### 5.2 前端环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8001/api/v1` |

---

## 6. 开发流程

### 6.1 本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1 -Q globaleads

# 前端
cd frontend
npm install
npm run dev
```

### 6.2 Docker Compose 开发

```bash
docker-compose up -d
```

### 6.3 提交代码

```bash
git checkout -b feature/xxx
# ... 编写代码 ...
git add <files>
git commit -m "feat: 添加 XXX 功能"
git push origin feature/xxx
# 合并到 dev → 测试 → 合并到 main → 部署
```
