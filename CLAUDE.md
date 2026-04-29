# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GlobalLeads is a B2B/social lead mining platform for Chinese foreign trade companies. It crawls overseas social media (Reddit, Bluesky, YouTube) and B2B sources (Apollo, Google Maps, Hunter.io), then uses LLM-based AI to analyze purchase intent and score leads.

## Development Commands

### Backend (Python 3.10+, FastAPI)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit with real keys

# Run API server (port 8002)
uvicorn app.main:app --port 8002 --reload

# Run Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1 -Q globaleads

# Docker Compose (dev DB + Redis only)
docker compose up -d  # PostgreSQL on :5433, Redis on :6380
```

### Frontend (React + TypeScript + Vite)
```bash
cd frontend
npm install
npm run dev       # dev server
npm run build     # tsc check + vite build
npm run preview   # preview production build
```

### Production Deploy
```bash
docker compose -f docker-compose.server.yml up -d --build
```

## Architecture

**Two-service system** deployed on the same Alibaba Cloud ECS, sharing PostgreSQL and Redis with a sibling project (LeadMine).

### Backend Layout (`backend/app/`)
- **`main.py`** — FastAPI entry with lifespan management, creates default admin on first run
- **`core/`** — Config (pydantic-settings from `.env`), async database, JWT security, dependency injection
- **`models/`** — SQLAlchemy 2.0 async ORM models (user, social_task, social_lead, b2b_task, b2b_lead)
- **`schemas/`** — Pydantic v2 request/response schemas
- **`api/v1/`** — Route handlers, all prefixed `/api/v1`
- **`services/`** — Business logic: platform API wrappers (reddit, bluesky, youtube, apollo, google_maps, hunter) and AI service
- **`tasks/`** — Celery async tasks (`social_crawl`, `b2b_search`) with `celery_app.py` configuration; tasks are explicitly imported to ensure registration
- **`middleware/`** — Request logging middleware with request_id tracing

### Frontend Layout (`frontend/src/`)
- **`pages/`** — Dashboard, SocialTasks, SocialLeads, B2BTasks, B2BLeads, Settings, Login
- **`services/`** — Axios-based API calls with JWT interceptor
- **`components/`** — Shared components (Layout, TaskForm, LeadTable, Charts)
- **`hooks/`** — Custom React hooks
- **`types/`** — TypeScript type definitions

### Core Data Flow
1. User creates task via API → saved to DB with `pending` status
2. Celery worker picks up task from `globaleads` queue
3. Service layer calls third-party APIs to collect data
4. AI service (Ollama/DeepSeek) analyzes collected content for purchase intent
5. Scored leads written to DB, task status updated to `completed`

### Key Design Decisions
- **AI provider switching**: `AI_PROVIDER` env var (`ollama` or `deepseek`), both use OpenAI-compatible API format
- **Shared infrastructure**: PostgreSQL uses DB name `globaleads` (vs `leadmine`), Redis uses DB 1 (vs DB 0), Celery uses queue name `globaleads`
- **Async throughout**: All DB operations use SQLAlchemy async sessions via `asyncpg`; all external API calls use `httpx` async
- **Logging**: Three rotating log files (`app.log`, `error.log`, `task.log`) with `request_id`/`task_id` tracing. Use `get_task_logger()` for Celery tasks, `get_service_logger()` for external service calls

## Conventions

### Git
- Commit format: `<type>: <subject>` (types: feat, fix, docs, refactor, test, chore)
- Branching: `main` (production), `feature/<name>`, `fix/<name>`

### Backend Code Style
- Python type hints required, async/await for all DB and external calls
- Business logic in Service layer, not in route handlers
- API routes use dependency injection: `Depends(get_db)` for DB session, `Depends(get_current_user)` for auth

### Frontend Code Style
- TypeScript strict mode, function components + Hooks
- Ant Design 5.x components; ProTable for data tables
- API calls through `services/` layer with centralized Axios instance

### Logging Format
```python
# Use | separator for key-value pairs (grep-friendly)
logger.info("操作描述 | key1=%s key2=%s", val1, val2)
# Errors must include exc_info=True
logger.error("操作失败 | error=%s", str(e), exc_info=True)
```
