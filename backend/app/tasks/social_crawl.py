"""
社媒爬取 Celery 异步任务

流程：
1. 获取任务配置
2. 调用各社媒 API 搜索（Reddit/Bluesky/YouTube）
3. AI 分析购买意向
4. 筛选出有意向的内容
5. 写入 social_leads 表
6. 更新任务状态
"""
import logging
import traceback
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.logging_config import setup_logging, get_task_logger

# Celery Worker 启动时初始化日志
setup_logging()
logger = get_task_logger("social_crawl")


def _get_sync_db():
    """获取同步数据库 session（Celery 不支持 async）"""
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_social_media(self, task_id: int):
    """
    社媒爬取异步任务

    Args:
        task_id: SocialTask 的 ID
    """
    db, engine = _get_sync_db()

    try:
        # 1. 获取任务配置
        from app.models.social_task import SocialTask
        from app.models.social_lead import SocialLead

        task = db.query(SocialTask).filter(SocialTask.id == task_id).first()
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        # 更新状态为 running
        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()

        keywords = task.keywords or []
        platforms = task.platforms or []
        max_results = task.max_results or 100
        min_score = task.min_score or 50

        all_raw_items = []

        # 2. 调用各社媒 API 搜索
        for platform in platforms:
            try:
                if platform == "reddit":
                    items = _crawl_reddit(keywords, max_results)
                elif platform == "bluesky":
                    items = _crawl_bluesky(keywords, max_results)
                elif platform == "youtube":
                    items = _crawl_youtube(keywords, max_results)
                else:
                    logger.warning(f"不支持的平台: {platform}")
                    continue

                for item in items:
                    item["platform"] = platform
                all_raw_items.extend(items)

            except Exception as e:
                logger.error(f"爬取 {platform} 失败: {e}")
                # 记录错误但继续其他平台
                continue

        if not all_raw_items:
            task.status = "completed"
            task.error_message = "未找到任何内容"
            task.updated_at = datetime.utcnow()
            db.commit()
            return

        # 3. AI 分析购买意向
        from app.services.ai_service import AISyncService
        ai_service = AISyncService()

        lead_count = 0
        for item in all_raw_items[:max_results]:
            try:
                content = item.get("content") or item.get("title", "")
                if not content or len(content.strip()) < 10:
                    continue

                ai_result = ai_service.analyze_purchase_intent(content, keywords)

                # 4. 筛选出有意向的内容（评分 >= min_score）
                if not ai_result.get("has_intent") or ai_result.get("score", 0) < min_score:
                    continue

                # 5. 提取联系方式（合并正则 + AI 提取结果）
                from app.services.contact_extractor import extract_contacts_from_text
                regex_contacts = extract_contacts_from_text(content)

                ai_contacts = ai_result.get("contacts", {})
                contact_email = ai_contacts.get("email") or (
                    regex_contacts["emails"][0] if regex_contacts["emails"] else None
                )
                contact_phone = ai_contacts.get("phone") or (
                    regex_contacts["phones"][0] if regex_contacts["phones"] else None
                )
                contact_website = ai_contacts.get("website") or (
                    regex_contacts["websites"][0] if regex_contacts["websites"] else None
                )
                contact_social = {}
                if ai_contacts.get("twitter") or regex_contacts["twitter"]:
                    contact_social["twitter"] = ai_contacts.get("twitter") or regex_contacts["twitter"][0]
                if ai_contacts.get("linkedin") or regex_contacts["linkedin"]:
                    contact_social["linkedin"] = ai_contacts.get("linkedin") or regex_contacts["linkedin"][0]
                if regex_contacts["facebook"]:
                    contact_social["facebook"] = regex_contacts["facebook"][0]
                if not contact_social:
                    contact_social = None

                # 6. 写入 social_leads 表
                # 去重检查：同平台同作者同内容
                existing = db.query(SocialLead).filter(
                    SocialLead.task_id == task_id,
                    SocialLead.platform == item.get("platform", ""),
                    SocialLead.author_name == item.get("author", "[unknown]"),
                    SocialLead.content == content,
                ).first()

                if existing:
                    continue

                lead = SocialLead(
                    task_id=task_id,
                    platform=item.get("platform", ""),
                    author_name=item.get("author", "[unknown]"),
                    author_url=item.get("author_url"),
                    content=content,
                    post_url=item.get("url"),
                    published_at=datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                    if item.get("published_at") else None,
                    ai_score=ai_result.get("score", 0),
                    ai_tags=ai_result.get("tags", []),
                    ai_analysis=ai_result.get("analysis", ""),
                    contact_email=contact_email,
                    contact_phone=contact_phone,
                    contact_website=contact_website,
                    contact_social=contact_social,
                    status="uncontacted",
                )
                db.add(lead)
                lead_count += 1

            except Exception as e:
                logger.error(f"分析内容失败: {e}")
                continue

        # 6. 更新任务状态
        task.status = "completed"
        task.lead_count = lead_count
        task.updated_at = datetime.utcnow()
        db.commit()

        # 更新 Redis API 用量统计
        _update_api_usage(platforms)

        logger.info(f"任务 {task_id} 完成，发现 {lead_count} 条线索")

    except Exception as e:
        db.rollback()
        logger.error(f"任务 {task_id} 失败: {traceback.format_exc()}")

        # 更新任务状态为 failed
        try:
            task = db.query(SocialTask).filter(SocialTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)[:500]
                task.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

        # 重试
        raise self.retry(exc=e)

    finally:
        db.close()
        engine.dispose()


def _crawl_reddit(keywords: list[str], max_results: int) -> list[dict]:
    """爬取 Reddit 帖子和评论"""
    from app.services.reddit_service import RedditSyncService

    reddit = RedditSyncService()
    items = []

    for keyword in keywords:
        try:
            posts = reddit.search_posts(keyword, limit=min(25, max_results // len(keywords)))
            for post in posts:
                # 添加帖子本身
                items.append({
                    "title": post.get("title", ""),
                    "content": post.get("title", "") + "\n\n" + post.get("content", ""),
                    "author": post.get("author", "[deleted]"),
                    "author_url": post.get("author_url", ""),
                    "url": post.get("url", ""),
                    "published_at": post.get("published_at"),
                })

                # 获取帖子评论
                if post.get("id") and post.get("subreddit"):
                    try:
                        comments = reddit.get_post_comments(
                            post["id"], post["subreddit"], limit=10
                        )
                        for comment in comments:
                            items.append({
                                "content": comment.get("content", ""),
                                "author": comment.get("author", "[deleted]"),
                                "author_url": comment.get("author_url", ""),
                                "url": post.get("url", ""),
                                "published_at": comment.get("published_at"),
                            })
                    except Exception as e:
                        logger.warning(f"获取 Reddit 评论失败: {e}")
                        continue

        except Exception as e:
            logger.error(f"搜索 Reddit 关键词 '{keyword}' 失败: {e}")
            continue

    return items[:max_results]


def _crawl_bluesky(keywords: list[str], max_results: int) -> list[dict]:
    """爬取 Bluesky 帖子"""
    from app.services.bluesky_service import BlueskySyncService

    bluesky = BlueskySyncService()
    items = []

    for keyword in keywords:
        try:
            posts = bluesky.search_posts(keyword, limit=min(25, max_results // len(keywords)))
            for post in posts:
                items.append({
                    "content": post.get("content", ""),
                    "author": post.get("author", ""),
                    "author_url": post.get("author_url", ""),
                    "url": post.get("url", ""),
                    "published_at": post.get("published_at"),
                })
        except Exception as e:
            logger.error(f"搜索 Bluesky 关键词 '{keyword}' 失败: {e}")
            continue

    return items[:max_results]


def _crawl_youtube(keywords: list[str], max_results: int) -> list[dict]:
    """爬取 YouTube 视频和评论"""
    from app.services.youtube_service import YouTubeSyncService

    youtube = YouTubeSyncService()
    items = []

    for keyword in keywords:
        try:
            videos = youtube.search_videos(keyword, max_results=min(10, max_results // len(keywords)))
            for video in videos:
                # 添加视频描述
                items.append({
                    "content": video.get("title", "") + "\n\n" + video.get("content", ""),
                    "author": video.get("channel", ""),
                    "author_url": video.get("channel_url", ""),
                    "url": video.get("url", ""),
                    "published_at": video.get("published_at"),
                })

                # 获取视频评论
                if video.get("id"):
                    try:
                        comments = youtube.get_video_comments(video["id"], max_results=10)
                        for comment in comments:
                            items.append({
                                "content": comment.get("content", ""),
                                "author": comment.get("author", ""),
                                "author_url": comment.get("author_url", ""),
                                "url": video.get("url", ""),
                                "published_at": comment.get("published_at"),
                            })
                    except Exception as e:
                        logger.warning(f"获取 YouTube 评论失败: {e}")
                        continue

        except Exception as e:
            logger.error(f"搜索 YouTube 关键词 '{keyword}' 失败: {e}")
            continue

    return items[:max_results]


def _update_api_usage(platforms: list[str]):
    """更新 Redis 中的 API 用量统计"""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for platform in platforms:
            key = f"api_usage:{platform}"
            r.incr(key)
        r.close()
    except Exception:
        pass
