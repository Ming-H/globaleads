# GlobalLeads 数据库设计文档

> 版本：v1.0
> 日期：2026-04-25
> 数据库：PostgreSQL 16
> 数据库名：globaleads

---

## 1. ER 关系图

```
users
  │
  ├── 1:N ──→ social_tasks
  │              │
  │              └── 1:N ──→ social_leads
  │
  ├── 1:N ──→ b2b_tasks
                 │
                 └── 1:N ──→ b2b_leads
```

两个功能模块完全独立，没有外键关联。

---

## 2. 表结构

### 2.1 users — 用户表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| hashed_password | VARCHAR(255) | NOT NULL | 加密密码 |
| is_active | BOOLEAN | DEFAULT true | 是否启用 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT now() | 更新时间 |

### 2.2 social_tasks — 社媒挖掘任务表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| user_id | INTEGER | FK → users.id, NOT NULL | 创建者 |
| name | VARCHAR(200) | NOT NULL | 任务名称 |
| keywords | JSONB | NOT NULL | 关键词列表 `["LED", "lighting"]` |
| platforms | JSONB | NOT NULL | 目标平台 `["reddit", "bluesky"]` |
| max_results | INTEGER | DEFAULT 100 | 最大采集数量 |
| min_score | INTEGER | DEFAULT 50 | 最低意向评分（低于此值不保存） |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/running/completed/failed/quota_exceeded |
| error_message | TEXT | NULL | 失败时的错误信息 |
| lead_count | INTEGER | DEFAULT 0 | 发现的线索数量 |
| celery_task_id | VARCHAR(255) | NULL | Celery 任务 ID |
| config | JSONB | DEFAULT '{}' | 额外配置（语言、地区等） |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT now() | 更新时间 |

### 2.3 social_leads — 社媒线索表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| task_id | INTEGER | FK → social_tasks.id, NOT NULL | 关联任务 |
| platform | VARCHAR(20) | NOT NULL | reddit/bluesky/youtube |
| author_name | VARCHAR(200) | NOT NULL | 发帖人昵称 |
| author_url | VARCHAR(500) | NULL | 发帖人主页链接 |
| content | TEXT | NOT NULL | 帖子/评论内容 |
| post_url | VARCHAR(500) | NULL | 原帖链接 |
| published_at | TIMESTAMP | NULL | 帖子发布时间 |
| ai_score | INTEGER | DEFAULT 0 | AI 意向评分 1-100 |
| ai_tags | JSONB | DEFAULT '[]' | AI 意向标签 `["求购", "找供应商"]` |
| ai_analysis | TEXT | NULL | AI 分析详细结果 |
| status | VARCHAR(20) | DEFAULT 'uncontacted' | uncontacted/contacted/replied/invalid |
| contact_email | VARCHAR(255) | NULL | 联系人邮箱 |
| contact_phone | VARCHAR(50) | NULL | 联系人电话 |
| contact_website | VARCHAR(500) | NULL | 联系人网站 |
| contact_social | JSONB | DEFAULT '{}' | 社交媒体链接 `{"twitter": "...", "linkedin": "..."}` |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

**索引：**
- `idx_social_leads_task_id` ON (task_id)
- `idx_social_leads_platform` ON (platform)
- `idx_social_leads_score` ON (ai_score DESC)
- `idx_social_leads_status` ON (status)

### 2.4 b2b_tasks — B2B 搜索任务表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| user_id | INTEGER | FK → users.id, NOT NULL | 创建者 |
| name | VARCHAR(200) | NOT NULL | 任务名称 |
| industry | VARCHAR(200) | NULL | 目标行业 |
| region | VARCHAR(200) | NULL | 目标地区 |
| company_size | VARCHAR(50) | NULL | 公司规模范围 |
| data_sources | JSONB | NOT NULL | 数据源 `["google_search", "osm"]` |
| max_results | INTEGER | DEFAULT 100 | 最大搜索数量 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/running/completed/failed/quota_exceeded |
| error_message | TEXT | NULL | 失败时的错误信息 |
| lead_count | INTEGER | DEFAULT 0 | 发现的线索数量 |
| celery_task_id | VARCHAR(255) | NULL | Celery 任务 ID |
| config | JSONB | DEFAULT '{}' | 额外配置 |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT now() | 更新时间 |

### 2.5 b2b_leads — B2B 线索表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| task_id | INTEGER | FK → b2b_tasks.id, NOT NULL | 关联任务 |
| company_name | VARCHAR(300) | NOT NULL | 公司名称 |
| company_website | VARCHAR(500) | NULL | 公司网站 |
| company_size | VARCHAR(50) | NULL | 公司规模 |
| company_address | VARCHAR(500) | NULL | 公司地址 |
| region | VARCHAR(200) | NULL | 所在地区 |
| industry | VARCHAR(200) | NULL | 行业分类 |
| contact_name | VARCHAR(200) | NULL | 联系人姓名 |
| contact_title | VARCHAR(200) | NULL | 联系人职位 |
| contact_email | VARCHAR(255) | NULL | 联系人邮箱 |
| contact_phone | VARCHAR(50) | NULL | 联系人电话 |
| contact_twitter | VARCHAR(200) | NULL | 联系人 Twitter |
| contact_linkedin | VARCHAR(200) | NULL | 联系人 LinkedIn |
| contact_facebook | VARCHAR(200) | NULL | 联系人 Facebook |
| data_source | VARCHAR(50) | NOT NULL | 数据来源：google_search/osm |
| source_url | VARCHAR(500) | NULL | 来源页面 URL |
| status | VARCHAR(20) | DEFAULT 'uncontacted' | uncontacted/contacted/replied/invalid |
| created_at | TIMESTAMP | DEFAULT now() | 创建时间 |

**索引：**
- `idx_b2b_leads_task_id` ON (task_id)
- `idx_b2b_leads_industry` ON (industry)
- `idx_b2b_leads_region` ON (region)
- `idx_b2b_leads_source` ON (data_source)
- `idx_b2b_leads_email` ON (contact_email)
- `idx_b2b_leads_status` ON (status)

---

## 3. 数据库初始化

应用启动时自动创建：
- 所有表结构
- 默认管理员账号（admin / admin123，首次登录后需修改密码）
