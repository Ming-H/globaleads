"""
Celery 配置和应用

使用 Redis 作为 broker 和 backend，队列名 globaleads。
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "globaleads",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,       # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    task_default_queue="globaleads",
    task_queues={
        "globaleads": {
            "exchange": "globaleads",
            "routing_key": "globaleads",
        },
    },
)

# 显式导入任务模块，确保 Celery Worker 注册任务
import app.tasks.social_crawl   # noqa: E402, F401
import app.tasks.b2b_search     # noqa: E402, F401
