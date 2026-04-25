# GlobalLeads — 海外线索挖掘平台

帮中国外贸/跨境电商企业，用 AI 从海外社交媒体和 B2B 渠道自动挖掘销售线索。

## 功能

- **社媒线索挖掘** — 在 Reddit/Bluesky/YouTube 搜索关键词，AI 分析购买意向，返回潜在客户
- **B2B 客户搜索** — 通过 Apollo/Google Maps API 搜索目标公司和联系人邮箱
- **线索管理** — 两个功能各自独立的线索池，支持筛选、排序、导出
- **数据看板** — 线索统计、趋势分析、API 用量监控

## 技术栈

- 后端：FastAPI + SQLAlchemy + Celery + Redis + PostgreSQL
- 前端：React + TypeScript + Ant Design + Vite
- AI：Ollama（测试）/ DeepSeek（生产）
- 部署：阿里云（后端）+ Vercel（前端）

## 文档

| 文档 | 说明 |
|------|------|
| [产品需求文档](docs/prd.md) | 功能定义、用户画像、里程碑 |
| [技术架构](docs/architecture.md) | 系统架构、模块设计、数据流 |
| [API 接口设计](docs/api.md) | 全部 REST API 定义 |
| [数据库设计](docs/database.md) | 表结构、索引、关系 |
| [前端设计](docs/frontend.md) | 页面结构、路由、组件设计 |
| [部署运维](docs/deployment.md) | 部署步骤、日常运维、回滚 |
| [测试计划](docs/testing.md) | 测试用例、集成测试 |
| [开发规范](docs/development-guide.md) | 代码风格、Git 规范、开发流程 |

## 快速开始

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 编辑配置
uvicorn app.main:app --port 8001 --reload
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env  # 编辑配置
npm run dev
```

## 部署

详见 [部署运维文档](docs/deployment.md)

- 后端：阿里云 Docker Compose
- 前端：Vercel（globaleads.devfoxai.cn）
- 代码：GitHub 私有仓库

## License

私有项目，未授权禁止使用。
