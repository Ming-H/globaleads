"""
B2B 搜索 Celery 异步任务

流程：
1. 获取任务配置
2. 调用 Apollo / Google Maps API 搜索公司
3. 获取公司列表 + 联系人
4. 调用 Hunter.io 获取邮箱
5. 邮箱验证
6. 写入 b2b_leads 表
7. 更新任务状态
"""
import logging
import traceback
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tasks.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_sync_db():
    """获取同步数据库 session"""
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def search_b2b_companies(self, task_id: int):
    """
    B2B 搜索异步任务

    Args:
        task_id: B2BTask 的 ID
    """
    db, engine = _get_sync_db()

    try:
        from app.models.b2b_task import B2BTask
        from app.models.b2b_lead import B2BLead

        task = db.query(B2BTask).filter(B2BTask.id == task_id).first()
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        # 更新状态为 running
        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()

        data_sources = task.data_sources or []
        industry = task.industry
        region = task.region
        company_size = task.company_size
        max_results = task.max_results or 100

        all_companies = []

        # 2. 调用各数据源 API 搜索公司
        for source in data_sources:
            try:
                if source == "apollo":
                    companies = _search_apollo(industry, region, company_size, max_results)
                elif source == "google_maps":
                    companies = _search_google_maps(industry, region, max_results)
                else:
                    logger.warning(f"不支持的数据源: {source}")
                    continue

                for company in companies:
                    company["data_source"] = source
                all_companies.extend(companies)

            except Exception as e:
                logger.error(f"搜索 {source} 失败: {e}")
                continue

        if not all_companies:
            task.status = "completed"
            task.error_message = "未找到任何公司"
            task.updated_at = datetime.utcnow()
            db.commit()
            return

        # 3. 获取联系人邮箱
        from app.services.hunter_service import HunterSyncService
        hunter = HunterSyncService()

        lead_count = 0
        for company in all_companies[:max_results]:
            try:
                # 尝试获取邮箱
                contact_email = None
                contact_name = None
                contact_title = None
                email_verified = False

                # 优先从 Apollo 直接获取联系人
                if company.get("data_source") == "apollo" and company.get("id"):
                    try:
                        from app.services.apollo_service import ApolloSyncService
                        apollo = ApolloSyncService()
                        contacts = apollo.get_contact_email(company["id"])
                        if contacts:
                            contact = contacts[0]
                            contact_email = contact.get("email")
                            contact_name = contact.get("name")
                            contact_title = contact.get("title")
                            email_verified = contact.get("email_status") == "verified"
                    except Exception:
                        pass

                # 如果没有邮箱，用 Hunter 查找
                if not contact_email and company.get("website"):
                    domain = _extract_domain(company.get("website", ""))
                    if domain:
                        try:
                            emails = hunter.domain_search(domain, limit=3)
                            if emails:
                                contact_email = emails[0].get("email")
                                contact_name = emails[0].get("full_name")
                                contact_title = emails[0].get("position")
                                email_verified = emails[0].get("verified", False)
                        except Exception:
                            pass

                # 去重检查：同任务同公司名
                existing = db.query(B2BLead).filter(
                    B2BLead.task_id == task_id,
                    B2BLead.company_name == company.get("company_name", ""),
                ).first()

                if existing:
                    continue

                # 5. 写入 b2b_leads 表
                lead = B2BLead(
                    task_id=task_id,
                    company_name=company.get("company_name", ""),
                    company_website=company.get("website"),
                    company_size=str(company.get("company_size", "")) if company.get("company_size") else company_size,
                    company_address=company.get("company_address") or company.get("address"),
                    region=company.get("region") or region,
                    industry=company.get("industry") or industry,
                    contact_name=contact_name,
                    contact_title=contact_title,
                    contact_email=contact_email,
                    contact_phone=company.get("phone"),
                    email_verified=email_verified,
                    data_source=company.get("data_source", ""),
                    source_url=company.get("linkedin_url") or company.get("url"),
                    status="uncontacted",
                )
                db.add(lead)
                lead_count += 1

            except Exception as e:
                logger.error(f"处理公司 {company.get('company_name', '')} 失败: {e}")
                continue

        # 6. 更新任务状态
        task.status = "completed"
        task.lead_count = lead_count
        task.updated_at = datetime.utcnow()
        db.commit()

        # 更新 API 用量统计
        _update_api_usage(data_sources)

        logger.info(f"B2B 任务 {task_id} 完成，发现 {lead_count} 条线索")

    except Exception as e:
        db.rollback()
        logger.error(f"B2B 任务 {task_id} 失败: {traceback.format_exc()}")

        try:
            task = db.query(B2BTask).filter(B2BTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)[:500]
                task.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=e)

    finally:
        db.close()
        engine.dispose()


def _search_apollo(
    industry: str | None,
    region: str | None,
    company_size: str | None,
    max_results: int,
) -> list[dict]:
    """通过 Apollo API 搜索公司"""
    from app.services.apollo_service import ApolloSyncService

    apollo = ApolloSyncService()
    all_companies = []
    page = 1

    while len(all_companies) < max_results:
        result = apollo.search_companies(
            industry=industry,
            region=region,
            company_size=company_size,
            page=page,
            per_page=min(25, max_results - len(all_companies)),
        )

        companies = result.get("companies", [])
        if not companies:
            break

        all_companies.extend(companies)
        page += 1

        if result.get("total", 0) <= page * 25:
            break

    return all_companies[:max_results]


def _search_google_maps(
    industry: str | None,
    region: str | None,
    max_results: int,
) -> list[dict]:
    """通过 Google Maps API 搜索公司"""
    from app.services.google_maps_service import GoogleMapsSyncService

    gmaps = GoogleMapsSyncService()
    query = f"{industry or 'business'} in {region or 'United States'}"
    places = gmaps.search_places(query)

    # 获取详细信息（含电话和网站）
    companies = []
    for place in places[:max_results]:
        if place.get("place_id"):
            try:
                details = gmaps.get_place_details(place["place_id"])
                companies.append({
                    **place,
                    "website": details.get("website"),
                    "phone": details.get("phone"),
                })
            except Exception:
                companies.append(place)
        else:
            companies.append(place)

    return companies


def _extract_domain(url: str) -> str | None:
    """从 URL 中提取域名"""
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return None


def _update_api_usage(data_sources: list[str]):
    """更新 Redis 中的 API 用量统计"""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for source in data_sources:
            key = f"api_usage:{source}"
            r.incr(key)
        # 也增加 hunter 用量（如果使用了的话）
        r.close()
    except Exception:
        pass
