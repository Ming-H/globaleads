"""
社媒任务接口 - CRUD + stop/retry
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.social_task import SocialTask
from app.schemas.social_task import SocialTaskCreate, SocialTaskResponse, SocialTaskListResponse

router = APIRouter()


@router.get("", response_model=SocialTaskListResponse)
async def list_social_tasks(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取社媒挖掘任务列表
    """
    query = select(SocialTask).where(SocialTask.user_id == current_user.id)

    if status_filter:
        query = query.where(SocialTask.status == status_filter)

    # 统计总数
    count_query = select(func.count()).select_from(SocialTask).where(SocialTask.user_id == current_user.id)
    if status_filter:
        count_query = count_query.where(SocialTask.status == status_filter)
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(SocialTask.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return SocialTaskListResponse(
        total=total,
        items=[SocialTaskResponse.model_validate(t) for t in tasks],
    )


@router.post("", response_model=SocialTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_social_task(
    request: SocialTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建社媒挖掘任务
    """
    task = SocialTask(
        user_id=current_user.id,
        name=request.name,
        keywords=request.keywords,
        platforms=request.platforms,
        max_results=request.max_results,
        min_score=request.min_score,
        status="pending",
        lead_count=0,
    )
    db.add(task)
    await db.flush()

    # 触发 Celery 异步任务
    from app.tasks.social_crawl import crawl_social_media
    celery_result = crawl_social_media.delay(task.id)
    task.celery_task_id = celery_result.id
    task.status = "running"
    await db.commit()
    await db.refresh(task)

    return SocialTaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=SocialTaskResponse)
async def get_social_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取社媒任务详情
    """
    result = await db.execute(
        select(SocialTask).where(SocialTask.id == task_id, SocialTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    return SocialTaskResponse.model_validate(task)


@router.post("/{task_id}/stop")
async def stop_social_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    停止正在运行的社媒任务
    """
    result = await db.execute(
        select(SocialTask).where(SocialTask.id == task_id, SocialTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if task.status != "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务不在运行状态")

    # 撤销 Celery 任务
    if task.celery_task_id:
        from app.tasks.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = "completed"
    await db.flush()

    return {"message": "任务已停止", "task_id": task.id}


@router.post("/{task_id}/retry")
async def retry_social_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    重试失败的社媒任务
    """
    result = await db.execute(
        select(SocialTask).where(SocialTask.id == task_id, SocialTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if task.status not in ("failed", "quota_exceeded"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能重试失败的任务")

    # 重新触发 Celery 任务
    from app.tasks.social_crawl import crawl_social_media
    celery_result = crawl_social_media.delay(task.id)
    task.celery_task_id = celery_result.id
    task.status = "running"
    task.error_message = None
    await db.flush()

    return {"message": "任务已重新开始", "task_id": task.id}
