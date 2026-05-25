"""
数据看板接口 - 统计 + 趋势
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.models.social_lead import SocialLead
from app.models.social_task import SocialTask
from app.models.b2b_lead import B2BLead
from app.models.b2b_task import B2BTask
from app.schemas.dashboard import (
    StatsResponse,
    SocialLeadsStats,
    B2BLeadsStats,
    TasksStats,
    APIUsage,
    TrendsResponse,
    TrendItem,
)

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取看板统计数据
    """
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)

    # --- 社媒线索统计 ---
    # 总数
    social_total = (await db.execute(
        select(func.count()).select_from(SocialLead).join(
            SocialTask, SocialLead.task_id == SocialTask.id
        ).where(SocialTask.user_id == current_user.id)
    )).scalar() or 0

    # 本周新增
    social_this_week = (await db.execute(
        select(func.count()).select_from(SocialLead).join(
            SocialTask, SocialLead.task_id == SocialTask.id
        ).where(SocialTask.user_id == current_user.id, SocialLead.created_at >= one_week_ago)
    )).scalar() or 0

    # 按平台分组
    platform_rows = (await db.execute(
        select(SocialLead.platform, func.count().label("cnt"))
        .join(SocialTask, SocialLead.task_id == SocialTask.id)
        .where(SocialTask.user_id == current_user.id)
        .group_by(SocialLead.platform)
    )).all()
    by_platform = {row.platform: row.cnt for row in platform_rows}

    # 平均评分
    avg_score = (await db.execute(
        select(func.avg(SocialLead.ai_score))
        .join(SocialTask, SocialLead.task_id == SocialTask.id)
        .where(SocialTask.user_id == current_user.id)
    )).scalar() or 0.0

    # 按标签分组（通过 JSONB 展开）
    tag_rows = (await db.execute(
        select(func.jsonb_array_elements_text(SocialLead.ai_tags).label("tag"), func.count().label("cnt"))
        .join(SocialTask, SocialLead.task_id == SocialTask.id)
        .where(SocialTask.user_id == current_user.id)
        .group_by("tag")
    )).all()
    by_tag = {row.tag: row.cnt for row in tag_rows}

    social_stats = SocialLeadsStats(
        total=social_total,
        this_week=social_this_week,
        by_platform=by_platform,
        avg_score=round(float(avg_score), 1),
        by_tag=by_tag,
    )

    # --- B2B 线索统计 ---
    b2b_total = (await db.execute(
        select(func.count()).select_from(B2BLead).join(
            B2BTask, B2BLead.task_id == B2BTask.id
        ).where(B2BTask.user_id == current_user.id)
    )).scalar() or 0

    b2b_this_week = (await db.execute(
        select(func.count()).select_from(B2BLead).join(
            B2BTask, B2BLead.task_id == B2BTask.id
        ).where(B2BTask.user_id == current_user.id, B2BLead.created_at >= one_week_ago)
    )).scalar() or 0

    source_rows = (await db.execute(
        select(B2BLead.data_source, func.count().label("cnt"))
        .join(B2BTask, B2BLead.task_id == B2BTask.id)
        .where(B2BTask.user_id == current_user.id)
        .group_by(B2BLead.data_source)
    )).all()
    by_source = {row.data_source: row.cnt for row in source_rows}

    with_email = (await db.execute(
        select(func.count()).select_from(B2BLead).join(
            B2BTask, B2BLead.task_id == B2BTask.id
        ).where(
            B2BTask.user_id == current_user.id,
            B2BLead.contact_email.isnot(None),
            B2BLead.contact_email != "",
        )
    )).scalar() or 0

    industry_rows = (await db.execute(
        select(B2BLead.industry, func.count().label("cnt"))
        .join(B2BTask, B2BLead.task_id == B2BTask.id)
        .where(B2BTask.user_id == current_user.id, B2BLead.industry.isnot(None))
        .group_by(B2BLead.industry)
    )).all()
    by_industry = {row.industry: row.cnt for row in industry_rows}

    b2b_stats = B2BLeadsStats(
        total=b2b_total,
        this_week=b2b_this_week,
        by_source=by_source,
        with_email=with_email,
        by_industry=by_industry,
    )

    # --- 任务统计 ---
    social_task_total = (await db.execute(
        select(func.count()).select_from(SocialTask).where(SocialTask.user_id == current_user.id)
    )).scalar() or 0

    b2b_task_total = (await db.execute(
        select(func.count()).select_from(B2BTask).where(B2BTask.user_id == current_user.id)
    )).scalar() or 0

    social_completed = (await db.execute(
        select(func.count()).select_from(SocialTask).where(
            SocialTask.user_id == current_user.id,
            SocialTask.status == "completed",
        )
    )).scalar() or 0

    b2b_completed = (await db.execute(
        select(func.count()).select_from(B2BTask).where(
            B2BTask.user_id == current_user.id,
            B2BTask.status == "completed",
        )
    )).scalar() or 0

    total_tasks = social_task_total + b2b_task_total
    total_completed = social_completed + b2b_completed
    success_rate = round(total_completed / total_tasks, 2) if total_tasks > 0 else 0.0

    tasks_stats = TasksStats(
        social_total=social_task_total,
        b2b_total=b2b_task_total,
        success_rate=success_rate,
    )

    # --- API 用量（从 Redis 获取，如无则返回默认） ---
    api_usage = {}
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for api_name, limit_str in [
            ("reddit", "60/min"),
            ("bluesky", "3000/5min"),
            ("youtube", "10000/day"),
            ("google_search", "100/day"),
            ("osm", "unlimited"),
        ]:
            used = int(r.get(f"api_usage:{api_name}" ) or 0)
            api_usage[api_name] = APIUsage(used=used, limit=limit_str)
        r.close()
    except Exception:
        api_usage = {
            "reddit": APIUsage(used=0, limit="60/min"),
            "bluesky": APIUsage(used=0, limit="3000/5min"),
            "youtube": APIUsage(used=0, limit="10000/day"),
            "google_search": APIUsage(used=0, limit="100/day"),
            "osm": APIUsage(used=0, limit="unlimited"),
        }

    return StatsResponse(
        social_leads=social_stats,
        b2b_leads=b2b_stats,
        tasks=tasks_stats,
        api_usage=api_usage,
    )


@router.get("/trends", response_model=TrendsResponse)
async def get_dashboard_trends(
    period: str = Query("day", pattern="^(day|week|month)$"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取趋势数据（按天/周/月）
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # 按天统计社媒线索
    social_rows = (await db.execute(
        select(
            func.date_trunc(period, SocialLead.created_at).label("date"),
            func.count().label("cnt"),
        )
        .join(SocialTask, SocialLead.task_id == SocialTask.id)
        .where(SocialTask.user_id == current_user.id, SocialLead.created_at >= start_date)
        .group_by("date")
        .order_by("date")
    )).all()

    social_map = {row.date.strftime("%Y-%m-%d"): row.cnt for row in social_rows if row.date}

    # 按天统计 B2B 线索
    b2b_rows = (await db.execute(
        select(
            func.date_trunc(period, B2BLead.created_at).label("date"),
            func.count().label("cnt"),
        )
        .join(B2BTask, B2BLead.task_id == B2BTask.id)
        .where(B2BTask.user_id == current_user.id, B2BLead.created_at >= start_date)
        .group_by("date")
        .order_by("date")
    )).all()

    b2b_map = {row.date.strftime("%Y-%m-%d"): row.cnt for row in b2b_rows if row.date}

    # 合并日期
    all_dates = sorted(set(list(social_map.keys()) + list(b2b_map.keys())))
    items = [
        TrendItem(
            date=d,
            social_leads=social_map.get(d, 0),
            b2b_leads=b2b_map.get(d, 0),
        )
        for d in all_dates
    ]

    return TrendsResponse(period=period, items=items)
