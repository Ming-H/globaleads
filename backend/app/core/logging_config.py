"""
日志系统配置

统一管理日志格式、Handler、轮转策略。
- app.log: 全部日志 INFO+（含 API 请求、认证、业务操作）
- error.log: 仅 ERROR+
- task.log: Celery 任务执行日志
- stdout: 同时输出到控制台（供 docker logs 查看）

日志文件通过 Docker Volume 挂载到宿主机，容器重建不丢失。
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 日志目录（容器内路径，Docker Volume 挂载到宿主机）
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")

# 日志格式
LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO"):
    """
    初始化全局日志配置

    Args:
        log_level: 日志级别，默认 INFO
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 根 logger 配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 避免重复添加 Handler（热重载场景）
    if root_logger.handlers:
        return

    # 1. 控制台输出（供 docker logs 查看）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # 2. app.log - 全部日志
    app_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)

    # 3. error.log - 仅错误
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "error.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=2,
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # 4. task.log - Celery 任务日志（独立 logger）
    task_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "task.log"),
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=2,
        encoding="utf-8",
    )
    task_handler.setFormatter(formatter)
    task_handler.setLevel(logging.INFO)

    task_logger = logging.getLogger("task")
    task_logger.addHandler(task_handler)
    task_logger.propagate = False  # 不传播到 root，避免 app.log 重复记录

    # 降低第三方库日志级别，减少噪音
    for noisy in ("uvicorn.access", "httpx", "httpcore", "asyncio", "celery.redirected"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("app").info("日志系统初始化完成 | dir=%s | level=%s", LOG_DIR, log_level)


def get_task_logger(task_name: str) -> logging.Logger:
    """
    获取 Celery 任务专用 logger

    Args:
        task_name: 任务名称，如 "social_crawl"

    Returns:
        配置好的 logger 实例，日志同时写入 task.log 和 app.log
    """
    logger = logging.getLogger(f"task.{task_name}")
    logger.setLevel(logging.INFO)
    # task.* 的父 logger "task" 已配置了 task.log handler
    return logger


def get_service_logger(service_name: str) -> logging.Logger:
    """
    获取业务服务专用 logger

    Args:
        service_name: 服务名称，如 "reddit", "ai"

    Returns:
        配置好的 logger 实例
    """
    return logging.getLogger(f"service.{service_name}")
