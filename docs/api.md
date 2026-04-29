# GlobalLeads API 接口设计文档

> 版本：v1.0
> 日期：2026-04-25
> Base URL: `http://<server>:8002/api/v1`

---

## 1. 认证接口

### POST /auth/login

用户登录，返回 JWT Token。

**请求体：**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应：**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 259200
}
```

### POST /auth/register

用户注册（MVP 阶段可仅限管理员创建）。

**请求体：**
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "password123"
}
```

---

## 2. 社媒任务接口

### GET /social-tasks

获取社媒挖掘任务列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 20 |
| status_filter | string | 筛选状态：pending/running/completed/failed |

**响应：**
```json
{
  "total": 50,
  "items": [
    {
      "id": 1,
      "name": "LED灯具Reddit挖掘",
      "keywords": ["LED lighting", "wholesale LED"],
      "platforms": ["reddit", "bluesky"],
      "status": "completed",
      "lead_count": 23,
      "error_message": null,
      "celery_task_id": "xxx-xxx-xxx",
      "config": {},
      "created_at": "2026-04-25T10:00:00Z",
      "updated_at": "2026-04-25T10:05:00Z"
    }
  ]
}
```

**字段说明：**
- `error_message`: 失败时的错误信息（仅 failed 状态有值）
- `celery_task_id`: Celery 异步任务 ID，用于追踪任务执行
- `config`: 额外配置（如语言、地区等）

### POST /social-tasks

创建社媒挖掘任务。

**请求体：**
```json
{
  "name": "LED灯具Reddit挖掘",
  "keywords": ["LED lighting", "wholesale LED", "LED supplier"],
  "platforms": ["reddit", "bluesky"],
  "max_results": 100,
  "min_score": 60
}
```

**响应：**
```json
{
  "id": 1,
  "name": "LED灯具Reddit挖掘",
  "keywords": ["LED lighting", "wholesale LED", "LED supplier"],
  "platforms": ["reddit", "bluesky"],
  "status": "pending",
  "lead_count": 0,
  "created_at": "2026-04-25T10:00:00Z"
}
```

### GET /social-tasks/{task_id}

获取任务详情。

### POST /social-tasks/{task_id}/stop

停止正在运行的任务。

### POST /social-tasks/{task_id}/retry

重试失败的任务。

---

## 3. 社媒线索接口

### GET /social-leads

获取社媒线索列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 20 |
| task_id | int | 按任务筛选 |
| platform | string | 按平台筛选：reddit/bluesky/youtube |
| min_score | int | 最低意向评分 |
| tag | string | 按意向标签筛选 |
| status_filter | string | 按联系状态：uncontacted/contacted/replied/invalid |
| sort_by | string | 排序字段：score/created_at |
| sort_order | string | asc/desc |

**响应：**
```json
{
  "total": 120,
  "items": [
    {
      "id": 1,
      "task_id": 1,
      "platform": "reddit",
      "author_name": "john_doe",
      "author_url": "https://reddit.com/user/john_doe",
      "content": "Looking for a reliable LED lighting supplier for my retail store...",
      "post_url": "https://reddit.com/r/...",
      "published_at": "2026-04-24T15:30:00Z",
      "ai_score": 85,
      "ai_tags": ["求购", "找供应商"],
      "ai_analysis": "该用户正在寻找LED照明供应商，表现出明确的采购意向...",
      "status": "uncontacted",
      "created_at": "2026-04-25T10:02:00Z"
    }
  ]
}
```

**字段说明：**
- `ai_analysis`: AI 分析的详细结果文本

### GET /social-leads/{lead_id}

获取线索详情。

### PATCH /social-leads/{lead_id}/status

更新线索联系状态。

**请求体：**
```json
{
  "status": "contacted"
}
```

### POST /social-leads/export

导出线索。

**请求体：**
```json
{
  "task_id": 1,
  "format": "csv",
  "filters": {
    "min_score": 60
  }
}
```

**响应：** 返回文件流（当前仅支持 CSV，Excel 导出待实现）

---

## 4. B2B 任务接口

### GET /b2b-tasks

获取 B2B 搜索任务列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| status_filter | string | 筛选状态 |

**响应：**
```json
{
  "total": 30,
  "items": [
    {
      "id": 1,
      "name": "美国LED经销商搜索",
      "industry": "Lighting",
      "region": "United States",
      "company_size": "11-50",
      "data_sources": ["apollo", "google_maps"],
      "status": "completed",
      "lead_count": 45,
      "created_at": "2026-04-25T10:00:00Z"
    }
  ]
}
```

### POST /b2b-tasks

创建 B2B 搜索任务。

**请求体：**
```json
{
  "name": "美国LED经销商搜索",
  "industry": "Lighting",
  "region": "United States",
  "company_size": "11-50",
  "data_sources": ["apollo", "google_maps"],
  "max_results": 100
}
```

### GET /b2b-tasks/{task_id}

获取任务详情。

### POST /b2b-tasks/{task_id}/stop

停止任务。

### POST /b2b-tasks/{task_id}/retry

重试任务。

---

## 5. B2B 线索接口

### GET /b2b-leads

获取 B2B 线索列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| task_id | int | 按任务筛选 |
| industry | string | 按行业筛选 |
| region | string | 按地区筛选 |
| data_source | string | 按数据源筛选：apollo/google_maps |
| has_email | bool | 是否有邮箱 |
| status_filter | string | 联系状态 |

**响应：**
```json
{
  "total": 45,
  "items": [
    {
      "id": 1,
      "task_id": 1,
      "company_name": "Bright LED Solutions Inc.",
      "company_website": "https://brightled.com",
      "company_size": "11-50",
      "company_address": "123 Main St, Los Angeles, CA",
      "region": "United States",
      "industry": "Lighting",
      "contact_name": "Sarah Johnson",
      "contact_title": "Purchasing Manager",
      "contact_email": "sarah@brightled.com",
      "contact_phone": "+1-555-0123",
      "email_verified": true,
      "data_source": "apollo",
      "source_url": "https://apollo.io/...",
      "status": "uncontacted",
      "created_at": "2026-04-25T10:03:00Z"
    }
  ]
}
```

**字段说明：**
- `contact_phone`: 联系人电话（可选）
- `source_url`: 来源页面 URL（Apollo/GMaps 原始链接）

### GET /b2b-leads/{lead_id}

获取线索详情。

### PATCH /b2b-leads/{lead_id}/status

更新线索联系状态。

### POST /b2b-leads/export

导出线索（当前仅支持 CSV，Excel 导出待实现）。

---

## 6. 数据看板接口

### GET /dashboard/stats

获取看板统计数据。

**响应：**
```json
{
  "social_leads": {
    "total": 120,
    "this_week": 35,
    "by_platform": {
      "reddit": 80,
      "bluesky": 30,
      "youtube": 10
    },
    "avg_score": 72,
    "by_tag": {
      "求购": 45,
      "找供应商": 30,
      "比价": 25,
      "问推荐": 20
    }
  },
  "b2b_leads": {
    "total": 200,
    "this_week": 50,
    "by_source": {
      "apollo": 150,
      "google_maps": 50
    },
    "with_email": 180,
    "by_industry": {
      "Lighting": 80,
      "Electronics": 60,
      "Manufacturing": 60
    }
  },
  "tasks": {
    "social_total": 50,
    "b2b_total": 30,
    "success_rate": 0.92
  },
  "api_usage": {
    "reddit": { "used": 1200, "limit": "60/min" },
    "bluesky": { "used": 800, "limit": "3000/5min" },
    "youtube": { "used": 500, "limit": 10000 },
    "apollo": { "used": 200, "limit": 900 },
    "google_maps": { "used": 500, "limit": 6250 },
    "hunter": { "used": 10, "limit": 25 }
  }
}
```

### GET /dashboard/trends

获取趋势数据（按天/周/月）。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| period | string | day/week/month |
| days | int | 统计天数，默认 30 |

---

## 7. 系统设置接口

### GET /settings/api-usage

查看各 API 当前用量和剩余额度。

**响应：**
```json
{
  "reddit": { "used": 1200, "limit": "60/min", "remaining": null },
  "bluesky": { "used": 800, "limit": "3000/5min", "remaining": null },
  "youtube": { "used": 500, "limit": 10000, "remaining": 9500 },
  "apollo": { "used": 200, "limit": 900, "remaining": 700 },
  "google_maps": { "used": 500, "limit": 6250, "remaining": 5750 },
  "hunter": { "used": 10, "limit": 25, "remaining": 15 }
}
```

> 注：`remaining` 字段仅对有月度/日度配额的 API 返回，速率限制类 API（Reddit/Bluesky）为 null。

### GET /settings/ai-config

查看当前 AI 配置（Ollama/DeepSeek）。

### PATCH /settings/ai-config

切换 AI 配置。

**请求体：**
```json
{
  "provider": "deepseek",
  "api_key": "sk-xxx"
}
```

---

## 8. 通用规范

### 认证方式

除 `/auth/login` 和 `/auth/register` 外，所有接口需在 Header 中携带：
```
Authorization: Bearer <token>
```

### 分页格式

所有列表接口统一返回：
```json
{
  "total": 100,
  "items": [...]
}
```

### 错误响应

```json
{
  "detail": "错误描述"
}
```

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
