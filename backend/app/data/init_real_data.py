"""真实数据初始化模块。

使用爬虫采集公开新闻数据，经过清洗管线处理后填充数据库：
- RiskCase: 有明确风险类型（非"其他"）的文章
- Enterprise: 从文章实体中提取的企业
- SentimentEvent: 所有清洗后的文章（external_id=url_hash 去重）

支持 `python -m app.data.init_real_data` 直接运行。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crawler.pipeline import CleanedArticle, CleaningPipeline
from app.crawler.scraper import NewsScraper
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)


class DataInitializer:
    """真实数据初始化编排器，串联爬虫→清洗→入库全流程。"""

    def __init__(self, db: Session):
        self.db = db
        self.scraper = NewsScraper()
        self.pipeline = CleaningPipeline()
        # retriever 在 run() 中延迟初始化（因为需要 embedding 模型加载）
        self._retriever = None

    def run(self) -> dict[str, Any]:
        """执行完整数据初始化流程，返回各阶段统计信息。"""
        # 1. 爬虫采集真实数据
        logger.info("开始采集真实数据...")
        raw_items = asyncio.run(self.scraper.fetch_all())
        logger.info("采集到 %d 条原始数据", len(raw_items))

        # 2. 清洗管线处理
        articles = self.pipeline.clean(raw_items)
        logger.info("清洗后剩余 %d 条有效文章", len(articles))

        # 3. 填充风险案例库（仅 risk_type != '其他'）
        cases_count = self._fill_cases(articles)
        logger.info("填充 %d 条风险案例", cases_count)

        # 4. 填充企业画像（从实体提取）
        ent_count = self._fill_enterprises(articles)
        logger.info("填充 %d 家企业", ent_count)

        # 5. 填充舆情事件（external_id 去重）
        event_count = self._fill_events(articles)
        logger.info("填充 %d 条舆情事件", event_count)

        # 5.5 更新企业风险评分历史（基于已创建的事件）
        self._update_enterprise_risk_histories()

        # 6. 同步向量索引（失败不阻塞）
        indexed = self._sync_vector_index()

        return {
            "fetched": len(raw_items),
            "cleaned": len(articles),
            "cases": cases_count,
            "enterprises": ent_count,
            "events": event_count,
            "indexed": indexed,
        }

    # ------------------------------------------------------------------
    # 填充风险案例
    # ------------------------------------------------------------------

    def _fill_cases(self, articles: list[CleanedArticle]) -> int:
        """筛选 risk_type != '其他' 的文章，按 title+source_url 去重后创建 RiskCase。"""
        # 查询已有案例的 title+source_url 组合
        existing: set[tuple[str, str]] = set()
        for row in self.db.query(RiskCase.title, RiskCase.source_url).all():
            existing.add((row.title or "", row.source_url or ""))

        count = 0
        for article in articles:
            # 仅收录有明确风险类型的文章
            if article.risk_type == "其他":
                continue

            dedup_key = (article.title, article.url)
            if dedup_key in existing:
                continue
            existing.add(dedup_key)

            case = RiskCase(
                title=article.title[:512],
                summary=article.cleaned_content,
                industry=article.industry,
                risk_type=article.risk_type,
                risk_level=article.risk_level,
                source_url=article.url,
                tags=article.tags,
                governance_playbook=article.governance_playbook,
            )
            self.db.add(case)
            count += 1

        self.db.commit()
        return count

    # ------------------------------------------------------------------
    # 填充企业画像
    # ------------------------------------------------------------------

    def _fill_enterprises(self, articles: list[CleanedArticle]) -> int:
        """从文章 entities 提取企业名称，按 name 去重后创建 Enterprise。"""
        existing_names: set[str] = {
            name for (name,) in self.db.query(Enterprise.name).all()
        }

        # 收集每个企业的信息（首次出现的文章属性）
        ent_info: dict[str, dict[str, Any]] = {}
        for article in articles:
            for entity in article.entities:
                if entity in existing_names:
                    continue
                if entity not in ent_info:
                    ent_info[entity] = {
                        "industry": article.industry,
                        "risk_type": article.risk_type,
                        "tags": list(article.tags),
                    }

        count = 0
        for name, info in ent_info.items():
            enterprise = Enterprise(
                name=name,
                industry=info["industry"],
                scale=self._guess_scale(name),
                region="",
                business_tags=info["tags"],
                risk_profile={"primary_risk": info["risk_type"]},
                risk_score_history=[],
            )
            self.db.add(enterprise)
            count += 1

        self.db.commit()
        return count

    def _guess_scale(self, name: str) -> str:
        """根据企业名称关键词猜测企业规模。"""
        if any(kw in name for kw in ["集团", "总公司", "股份", "控股"]):
            return "大型"
        if any(kw in name for kw in ["小店", "工作室", "个体", "便利店"]):
            return "小型"
        return "中型"

    # ------------------------------------------------------------------
    # 填充舆情事件
    # ------------------------------------------------------------------

    def _fill_events(self, articles: list[CleanedArticle]) -> int:
        """填充 SentimentEvent，通过 external_id (url_hash) 去重。"""
        # 查询已有 external_id 集合
        existing_ids: set[str] = {
            eid for (eid,) in self.db.query(SentimentEvent.external_id).all()
            if eid
        }

        count = 0
        for article in articles:
            if article.url_hash in existing_ids:
                continue
            existing_ids.add(article.url_hash)

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
            self.db.add(event)
            count += 1

        self.db.commit()
        return count

    # ------------------------------------------------------------------
    # 企业风险评分历史
    # ------------------------------------------------------------------

    def _update_enterprise_risk_histories(self):
        """为所有企业更新 6 个月风险评分历史。"""
        enterprises = self.db.query(Enterprise).all()
        for ent in enterprises:
            ent.risk_score_history = self._compute_enterprise_risk_history(ent)
        self.db.commit()

    def _compute_enterprise_risk_history(
        self, enterprise: Enterprise
    ) -> list[dict[str, Any]]:
        """基于该企业关联的 SentimentEvent 计算 6 个月风险评分趋势。

        Returns:
            包含 6 个月数据的列表，每项格式: {"month": "YYYY-MM", "score": float}
        """
        now = datetime.now()
        history: list[dict[str, Any]] = []

        for i in range(5, -1, -1):
            month_key, start, end = self._get_month_range(now, i)

            # 查询该月该企业的舆情事件
            events = (
                self.db.query(SentimentEvent)
                .filter(SentimentEvent.enterprise_name == enterprise.name)
                .filter(SentimentEvent.created_at >= start)
                .filter(SentimentEvent.created_at < end)
                .all()
            )

            if events:
                avg_score = sum(e.risk_score or 0.0 for e in events) / len(events)
            else:
                avg_score = 0.0

            history.append({"month": month_key, "score": round(avg_score, 4)})

        return history

    @staticmethod
    def _get_month_range(
        now: datetime, months_ago: int
    ) -> tuple[str, datetime, datetime]:
        """计算 N 个月前的月份范围 [start, end)。"""
        year = now.year
        month = now.month - months_ago
        while month <= 0:
            month += 12
            year -= 1

        month_key = f"{year}-{month:02d}"
        start = datetime(year, month, 1)

        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        return (month_key, start, end)

    # ------------------------------------------------------------------
    # 向量索引同步
    # ------------------------------------------------------------------

    def _sync_vector_index(self) -> int:
        """同步向量索引，调用 retriever.index_case / index_enterprise。

        失败仅记录日志不阻塞主流程。
        """
        indexed = 0
        try:
            from app.rag.retriever import HybridRetriever

            self._retriever = HybridRetriever(self.db)

            # 索引风险案例
            for case in self.db.query(RiskCase).all():
                try:
                    self._retriever.index_case(case)
                    case.vector_id = str(case.id)
                    indexed += 1
                except Exception as e:
                    logger.warning("案例 %s 向量索引失败: %s", case.id, e)

            # 索引企业
            for ent in self.db.query(Enterprise).all():
                try:
                    self._retriever.index_enterprise(ent)
                    ent.vector_id = str(ent.id)
                    indexed += 1
                except Exception as e:
                    logger.warning("企业 %s 向量索引失败: %s", ent.id, e)

            self.db.commit()
        except Exception as e:
            logger.warning("向量索引初始化失败（不阻塞）: %s", e)

        return indexed


if __name__ == "__main__":
    from app.models.base import Base, SessionLocal, engine

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        initializer = DataInitializer(db)
        result = initializer.run()
        print(f"\n真实数据初始化完成: {result}")
    finally:
        db.close()
