"""
B2B 线索接口 - 列表（筛选/分页）+ 状态更新 + 导出
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.b2b_lead import B2BLead
from app.models.b2b_task import B2BTask
from app.schemas.b2b_lead import (
    B2BLeadResponse,
    B2BLeadListResponse,
    B2BLeadStatusUpdate,
    ExportRequest,
)

router = APIRouter()


@router.get("", response_model=B2BLeadListResponse)
async def list_b2b_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_id: int | None = None,
    industry: str | None = None,
    region: str | None = None,
    data_source: str | None = None,
    has_email: bool | None = None,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 B2B 线索列表，支持多维度筛选
    """
    query = select(B2BLead).join(
        B2BTask, B2BLead.task_id == B2BTask.id
    ).where(B2BTask.user_id == current_user.id)

    count_query = select(func.count()).select_from(B2BLead).join(
        B2BTask, B2BLead.task_id == B2BTask.id
    ).where(B2BTask.user_id == current_user.id)

    # 筛选条件
    if task_id is not None:
        query = query.where(B2BLead.task_id == task_id)
        count_query = count_query.where(B2BLead.task_id == task_id)
    if industry:
        query = query.where(B2BLead.industry == industry)
        count_query = count_query.where(B2BLead.industry == industry)
    if region:
        query = query.where(B2BLead.region == region)
        count_query = count_query.where(B2BLead.region == region)
    if data_source:
        query = query.where(B2BLead.data_source == data_source)
        count_query = count_query.where(B2BLead.data_source == data_source)
    if has_email is True:
        query = query.where(B2BLead.contact_email.isnot(None), B2BLead.contact_email != "")
        count_query = count_query.where(B2BLead.contact_email.isnot(None), B2BLead.contact_email != "")
    if status_filter:
        query = query.where(B2BLead.status == status_filter)
        count_query = count_query.where(B2BLead.status == status_filter)

    # 统计总数
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(B2BLead.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    leads = result.scalars().all()

    return B2BLeadListResponse(
        total=total,
        items=[B2BLeadResponse.model_validate(lead) for lead in leads],
    )


@router.get("/{lead_id}", response_model=B2BLeadResponse)
async def get_b2b_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 B2B 线索详情
    """
    result = await db.execute(
        select(B2BLead).join(
            B2BTask, B2BLead.task_id == B2BTask.id
        ).where(B2BLead.id == lead_id, B2BTask.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索不存在")

    return B2BLeadResponse.model_validate(lead)


@router.patch("/{lead_id}/status", response_model=B2BLeadResponse)
async def update_b2b_lead_status(
    lead_id: int,
    request: B2BLeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新 B2B 线索联系状态
    """
    result = await db.execute(
        select(B2BLead).join(
            B2BTask, B2BLead.task_id == B2BTask.id
        ).where(B2BLead.id == lead_id, B2BTask.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索不存在")

    lead.status = request.status
    await db.flush()

    return B2BLeadResponse.model_validate(lead)


@router.post("/export")
async def export_b2b_leads(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导出 B2B 线索为 CSV 文件
    """
    query = select(B2BLead).join(
        B2BTask, B2BLead.task_id == B2BTask.id
    ).where(B2BTask.user_id == current_user.id)

    if request.task_id:
        query = query.where(B2BLead.task_id == request.task_id)

    industry = request.filters.get("industry")
    if industry:
        query = query.where(B2BLead.industry == industry)

    region = request.filters.get("region")
    if region:
        query = query.where(B2BLead.region == region)

    has_email = request.filters.get("has_email")
    if has_email:
        query = query.where(B2BLead.contact_email.isnot(None), B2BLead.contact_email != "")

    query = query.order_by(B2BLead.created_at.desc())
    result = await db.execute(query)
    leads = result.scalars().all()

    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "任务ID", "公司名称", "公司网站", "公司规模",
        "公司地址", "地区", "行业", "联系人", "职位",
        "邮箱", "电话", "邮箱已验证", "数据来源", "来源URL",
        "状态", "创建时间",
    ])
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.task_id,
            lead.company_name,
            lead.company_website or "",
            lead.company_size or "",
            lead.company_address or "",
            lead.region or "",
            lead.industry or "",
            lead.contact_name or "",
            lead.contact_title or "",
            lead.contact_email or "",
            lead.contact_phone or "",
            lead.email_verified,
            lead.data_source,
            lead.source_url or "",
            lead.status,
            lead.created_at.isoformat() if lead.created_at else "",
        ])

    output.seek(0)
    filename = f"b2b_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
