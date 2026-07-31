"""爬虫定时采集调度器。

使用 asyncio 实现每 30 分钟自动触发一次爬虫采集。
"""

import asyncio
import logging
from datetime import UTC, datetime

from app.crawler.pipeline import CleaningPipeline
from app.crawler.scraper import NewsScraper
from app.models.base import SessionLocal
from app.models.crawler_log import CrawlerLog
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 30 * 60  # 30 分钟


async def _run_crawler_once() -> None:
    """执行一次爬虫采集并记录日志。"""
    db = SessionLocal()
    try:
        scraper = NewsScraper()
        raw_items = await scraper.fetch_all()
        pipeline = CleaningPipeline()
        articles = pipeline.clean(raw_items)

        existing_ids = {
            row.external_id
            for row in db.query(SentimentEvent.external_id).all()
            if row.external_id
        }

        persisted = 0
        deduped = 0
        for article in articles:
            if article.url_hash in existing_ids:
                deduped += 1
                continue
            if not article.title or not article.cleaned_content or not article.source_name:
                continue
            if article.risk_level not in ("低", "中", "高", "极高"):
                continue
            event = SentimentEvent(
                title=article.title[:512],
                content=article.cleaned_content,
                source=article.source_name,
                url=article.url,
                external_id=article.url_hash,
                enterprise_name=article.entities[0] if article.entities else None,
                risk_level=article.risk_level,
                risk_type=article.risk_type,
                risk_score=article.risk_score,
                governance_plan=article.governance_playbook,
                status="processed",
            )
            db.add(event)
            persisted += 1
        db.commit()

        # 成功的源列表
        detail = scraper._last_run_status.get("sources_detail", [])
        sources_ok = [s["name"] for s in detail if s.get("ok")]
        sources_failed = [s["name"] for s in detail if not s.get("ok")]

        db.add(CrawlerLog(
            fetched=len(raw_items),
            cleaned=len(articles),
            persisted=persisted,
            deduped=deduped,
            sources_ok=",".join(sources_ok),
            sources_failed=",".join(sources_failed),
        ))
        db.commit()
        logger.info(
            "定时采集完成: fetched=%d, cleaned=%d, persisted=%d, deduped=%d",
            len(raw_items), len(articles), persisted, deduped,
        )
    except Exception as e:
        logger.error("定时采集失败: %s", e)
        try:
            db.add(CrawlerLog(
                fetched=0,
                cleaned=0,
                persisted=0,
                deduped=0,
                sources_ok="",
                sources_failed="",
                error=str(e)[:500],
            ))
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def scheduler_loop() -> None:
    """定时采集主循环，每 30 分钟执行一次。"""
    logger.info("爬虫定时采集调度器已启动，间隔 %d 秒", INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        logger.info("定时采集触发: %s", datetime.now(UTC).isoformat())
        await _run_crawler_once()
