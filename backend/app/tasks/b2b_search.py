"""
B2B 搜索 Celery 异步任务

流程：
1. 获取任务配置
2. Google Custom Search 搜索公司网站
3. OpenStreetMap Nominatim 搜索本地商家
4. 合并去重结果
5. 对每个公司网站抓取联系方式
6. 写入 b2b_leads 表
7. 更新任务状态
"""
import logging
import traceback
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.logging_config import setup_logging, get_task_logger

setup_logging()
logger = get_task_logger("b2b_search")


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

        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()

        data_sources = task.data_sources or []
        industry = task.industry or "business"
        region = task.region or ""
        company_size = task.company_size
        max_results = task.max_results or 100

        all_companies = []

        # 2. 调用各免费数据源搜索公司
        for source in data_sources:
            try:
                if source == "google_search":
                    companies = _search_google(industry, region, max_results)
                elif source == "osm":
                    companies = _search_osm(industry, region, max_results)
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

        # 3. 对每个公司提取联系方式
        from app.services.contact_extractor import extract_contacts_from_website

        lead_count = 0
        seen_names = set()

        for company in all_companies[:max_results]:
            try:
                company_name = company.get("company_name") or company.get("name", "")
                if not company_name or company_name in seen_names:
                    continue

                # 去重检查：同任务同公司名
                existing = db.query(B2BLead).filter(
                    B2BLead.task_id == task_id,
                    B2BLead.company_name == company_name,
                ).first()
                if existing:
                    continue

                seen_names.add(company_name)

                # 提取联系方式
                contact_email = company.get("email")
                contact_phone = company.get("phone")
                contact_twitter = None
                contact_linkedin = None
                contact_facebook = None
                website = company.get("website") or company.get("url")

                # 如果有网站，尝试抓取联系方式
                if website:
                    try:
                        web_contacts = extract_contacts_from_website(website)
                        if not contact_email and web_contacts["emails"]:
                            contact_email = web_contacts["emails"][0]
                        if not contact_phone and web_contacts["phones"]:
                            contact_phone = web_contacts["phones"][0]
                        if web_contacts["twitter"]:
                            contact_twitter = web_contacts["twitter"][0]
                        if web_contacts["linkedin"]:
                            contact_linkedin = web_contacts["linkedin"][0]
                        if web_contacts["facebook"]:
                            contact_facebook = web_contacts["facebook"][0]
                    except Exception as e:
                        logger.warning(f"抓取网站联系方式失败: {website}, {e}")

                lead = B2BLead(
                    task_id=task_id,
                    company_name=company_name,
                    company_website=website,
                    company_size=company_size,
                    company_address=company.get("address") or company.get("company_address"),
                    region=company.get("region") or region,
                    industry=company.get("industry") or industry,
                    contact_email=contact_email,
                    contact_phone=contact_phone,
                    contact_twitter=contact_twitter,
                    contact_linkedin=contact_linkedin,
                    contact_facebook=contact_facebook,
                    data_source=company.get("data_source", ""),
                    source_url=website,
                    status="uncontacted",
                )
                db.add(lead)
                lead_count += 1

            except Exception as e:
                logger.error(f"处理公司 {company.get('company_name') or company.get('name', '')} 失败: {e}")
                continue

        task.status = "completed"
        task.lead_count = lead_count
        task.updated_at = datetime.utcnow()
        db.commit()

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


def _search_google(industry: str, region: str, max_results: int) -> list[dict]:
    """通过 Google Custom Search 搜索公司"""
    from app.services.google_search_service import GoogleSearchSyncService

    service = GoogleSearchSyncService()
    query = f"{industry} companies"
    if region:
        query += f" in {region}"

    try:
        results = service.search_companies(query, max_results=min(10, max_results))
    except RuntimeError as e:
        logger.warning(f"Google Search 配额已满: {e}")
        return []

    companies = []
    for r in results:
        companies.append({
            "company_name": r.get("title", "").split(" - ")[0].split(" | ")[0],
            "website": r.get("url", ""),
            "snippet": r.get("snippet", ""),
        })

    return companies


def _search_osm(industry: str, region: str, max_results: int) -> list[dict]:
    """通过 OpenStreetMap Nominatim 搜索本地商家"""
    from app.services.osm_service import OSMSyncService

    service = OSMSyncService()
    query = f"{industry}"
    try:
        results = service.search_businesses(query, region=region, limit=min(20, max_results))
    except Exception as e:
        logger.warning(f"OSM 搜索失败: {e}")
        return []

    companies = []
    for r in results:
        companies.append({
            "company_name": r.get("name", ""),
            "address": r.get("address", ""),
            "phone": r.get("phone", ""),
            "email": r.get("email", ""),
            "website": r.get("website", ""),
            "display_name": r.get("display_name", ""),
        })

    return companies


def _update_api_usage(data_sources: list[str]):
    """更新 Redis 中的 API 用量统计"""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for source in data_sources:
            key = f"api_usage:{source}"
            r.incr(key)
        r.close()
    except Exception:
        pass
