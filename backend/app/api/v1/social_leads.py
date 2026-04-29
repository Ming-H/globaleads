"""
社媒线索接口 - 列表（筛选/分页）+ 状态更新 + 导出
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from openpyxl import Workbook

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.social_lead import SocialLead
from app.models.social_task import SocialTask
from app.schemas.social_lead import (
    SocialLeadResponse,
    SocialLeadListResponse,
    SocialLeadStatusUpdate,
    ExportRequest,
)

router = APIRouter()


@router.get("", response_model=SocialLeadListResponse)
async def list_social_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_id: int | None = None,
    platform: str | None = None,
    min_score: int | None = None,
    tag: str | None = None,
    status_filter: str | None = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取社媒线索列表，支持多维度筛选和排序
    """
    # 基础查询：只查询当前用户的线索
    query = select(SocialLead).join(
        SocialTask, SocialLead.task_id == SocialTask.id
    ).where(SocialTask.user_id == current_user.id)

    count_query = select(func.count()).select_from(SocialLead).join(
        SocialTask, SocialLead.task_id == SocialTask.id
    ).where(SocialTask.user_id == current_user.id)

    # 筛选条件
    if task_id is not None:
        query = query.where(SocialLead.task_id == task_id)
        count_query = count_query.where(SocialLead.task_id == task_id)
    if platform:
        query = query.where(SocialLead.platform == platform)
        count_query = count_query.where(SocialLead.platform == platform)
    if min_score is not None:
        query = query.where(SocialLead.ai_score >= min_score)
        count_query = count_query.where(SocialLead.ai_score >= min_score)
    if tag:
        query = query.where(SocialLead.ai_tags.contains([tag]))
        count_query = count_query.where(SocialLead.ai_tags.contains([tag]))
    if status_filter:
        query = query.where(SocialLead.status == status_filter)
        count_query = count_query.where(SocialLead.status == status_filter)

    # 统计总数
    total = (await db.execute(count_query)).scalar() or 0

    # 排序
    sort_column = getattr(SocialLead, sort_by, SocialLead.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        if sort_by == "ai_score":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    leads = result.scalars().all()

    return SocialLeadListResponse(
        total=total,
        items=[SocialLeadResponse.model_validate(lead) for lead in leads],
    )


@router.get("/{lead_id}", response_model=SocialLeadResponse)
async def get_social_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取社媒线索详情
    """
    result = await db.execute(
        select(SocialLead).join(
            SocialTask, SocialLead.task_id == SocialTask.id
        ).where(SocialLead.id == lead_id, SocialTask.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索不存在")

    return SocialLeadResponse.model_validate(lead)


@router.patch("/{lead_id}/status", response_model=SocialLeadResponse)
async def update_social_lead_status(
    lead_id: int,
    request: SocialLeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新社媒线索联系状态
    """
    result = await db.execute(
        select(SocialLead).join(
            SocialTask, SocialLead.task_id == SocialTask.id
        ).where(SocialLead.id == lead_id, SocialTask.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索不存在")

    lead.status = request.status
    await db.flush()

    return SocialLeadResponse.model_validate(lead)


@router.post("/export")
async def export_social_leads(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导出社媒线索为 CSV/Excel 文件
    """
    query = select(SocialLead).join(
        SocialTask, SocialLead.task_id == SocialTask.id
    ).where(SocialTask.user_id == current_user.id)

    if request.task_id:
        query = query.where(SocialLead.task_id == request.task_id)

    min_score = request.filters.get("min_score")
    if min_score:
        query = query.where(SocialLead.ai_score >= int(min_score))

    platform = request.filters.get("platform")
    if platform:
        query = query.where(SocialLead.platform == platform)

    query = query.order_by(SocialLead.ai_score.desc())
    result = await db.execute(query)
    leads = result.scalars().all()

    # 表头和数据行
    headers = [
        "ID", "任务ID", "平台", "作者", "作者链接",
        "内容", "帖子链接", "发布时间", "AI评分",
        "AI标签", "状态", "创建时间",
    ]
    rows = []
    for lead in leads:
        rows.append([
            lead.id,
            lead.task_id,
            lead.platform,
            lead.author_name,
            lead.author_url or "",
            lead.content,
            lead.post_url or "",
            lead.published_at.isoformat() if lead.published_at else "",
            lead.ai_score,
            ",".join(lead.ai_tags) if lead.ai_tags else "",
            lead.status,
            lead.created_at.isoformat() if lead.created_at else "",
        ])

    filename_base = f"social_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 根据格式导出
    if request.format == "xlsx":
        # 生成 Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "社媒线索"
        ws.append(headers)
        for row in rows:
            ws.append(row)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"{filename_base}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    else:
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)

        output.seek(0)
        filename = f"{filename_base}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
