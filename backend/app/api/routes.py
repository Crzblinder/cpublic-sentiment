import csv
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas import AbTestRequest, EventResponse, LabelRequest, SentimentAnalyzeRequest
from app.config import get_settings
from app.crawler.pipeline import CleaningPipeline
from app.crawler.scraper import NewsScraper
from app.crawler.scraper import get_status as crawler_get_status
from app.models.analysis_history import AnalysisHistory
from app.models.base import get_db
from app.models.case import RiskCase
from app.models.crawler_log import CrawlerLog
from app.models.enterprise import Enterprise
from app.models.sentiment import SentimentEvent
from app.services.dashboard_service import DashboardService
from app.services.evaluation_service import EvaluationService
from app.services.sentiment_service import SentimentService

api_router = APIRouter()


# ---- 舆情分析 ----

@api_router.post("/sentiment/analyze")
def analyze_sentiment(
    req: SentimentAnalyzeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = SentimentService(db)
    return service.analyze(
        text=req.text,
        source=req.source,
        enterprise_hint=req.enterprise_hint,
        prompt_variants=req.prompt_variants,
    )


@api_router.post("/sentiment/analyze/stream")
async def analyze_stream(
    req: SentimentAnalyzeRequest,
    db: Session = Depends(get_db),
):
    """SSE 流式舆情分析：每个 Agent 节点完成时推送中间结果。"""
    import time

    from app.agents.workflow import _format_result, build_sentiment_graph, persist_event

    graph = build_sentiment_graph(db, prompt_variants=req.prompt_variants)

    initial_state = {
        "text": req.text,
        "enterprise_hint": req.enterprise_hint,
        "prompt_variants": req.prompt_variants,
        "reasoning_chain": [],
        "stream_events": [],
    }

    async def event_generator():
        start_time = time.time()
        running_state: dict[str, Any] = dict(initial_state)

        async for event in graph.astream(initial_state, stream_mode="updates"):
            elapsed = int((time.time() - start_time) * 1000)
            for update in event.values():
                if isinstance(update, dict):
                    running_state.update(update)
            payload = json.dumps(
                {"node_update": event, "elapsed_ms": elapsed},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"

        # 直接从累加状态生成最终结果并持久化，避免二次 invoke
        elapsed = int((time.time() - start_time) * 1000)
        result = _format_result(running_state, elapsed, req.prompt_variants)
        event_id = persist_event(db, req.text, result, source=req.source)
        result["event_id"] = event_id
        final_payload = json.dumps(
            {"final_result": result}, ensure_ascii=False,
        )
        yield f"data: {final_payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api_router.get("/sentiment/events", response_model=list[EventResponse])
def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    risk_level: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SentimentEvent).filter(SentimentEvent.status == "processed")
    if risk_level:
        q = q.filter(SentimentEvent.risk_level == risk_level)
    events = q.order_by(SentimentEvent.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "risk_level": e.risk_level,
            "risk_type": e.risk_type,
            "risk_score": e.risk_score,
            "source": e.source,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@api_router.get("/sentiment/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(SentimentEvent).filter(SentimentEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": event.id,
        "title": event.title,
        "content": event.content,
        "risk_level": event.risk_level,
        "risk_type": event.risk_type,
        "risk_score": event.risk_score,
        "enterprise_name": event.enterprise_name,
        "matched_case_ids": event.matched_case_ids,
        "governance_plan": event.governance_plan,
        "reasoning_chain": event.reasoning_chain,
        "response_time_ms": event.response_time_ms,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@api_router.post("/sentiment/label")
def label_event(req: LabelRequest, db: Session = Depends(get_db)):
    event = db.query(SentimentEvent).filter(SentimentEvent.id == req.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.labeled_risk_level = req.true_risk_level
    event.is_correct = int(event.risk_level == req.true_risk_level)
    db.commit()
    return {"event_id": event.id, "is_correct": event.is_correct}


# ---- 仪表盘统计 ----

@api_router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_stats()


@api_router.get("/dashboard/trend")
def dashboard_trend(days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_trend(days=days)


# ---- 案例库 ----

@api_router.get("/cases")
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    industry: str | None = None,
    risk_type: str | None = None,
    risk_level: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(RiskCase)
    if industry:
        q = q.filter(RiskCase.industry == industry)
    if risk_type:
        q = q.filter(RiskCase.risk_type == risk_type)
    if risk_level:
        q = q.filter(RiskCase.risk_level == risk_level)
    if search:
        q = q.filter(RiskCase.title.contains(search) | RiskCase.summary.contains(search))
    total = q.count()
    cases = q.order_by(RiskCase.id.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "title": c.title,
                "industry": c.industry,
                "risk_type": c.risk_type,
                "risk_level": c.risk_level,
                "summary": c.summary[:200],
                "governance_playbook": c.governance_playbook,
            }
            for c in cases
        ],
    }


# ---- 企业画像 ----

@api_router.get("/enterprises")
def list_enterprises(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    industry: str | None = None,
    region: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Enterprise)
    if industry:
        q = q.filter(Enterprise.industry == industry)
    if region:
        q = q.filter(Enterprise.region == region)
    if search:
        q = q.filter(Enterprise.name.contains(search))
    total = q.count()
    enterprises = q.offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "industry": e.industry,
                "scale": e.scale,
                "region": e.region,
                "business_tags": e.business_tags or [],
                "risk_profile": e.risk_profile or {},
                "risk_score_history": e.risk_score_history or [],
            }
            for e in enterprises
        ],
    }


@api_router.get("/enterprises/{enterprise_id}")
def get_enterprise_detail(enterprise_id: int, db: Session = Depends(get_db)):
    service = DashboardService(db)
    detail = service.get_enterprise_detail(enterprise_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    return detail


@api_router.get("/enterprises/{enterprise_id}/events")
def get_enterprise_events(
    enterprise_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return service.get_enterprise_events(enterprise_id, skip=skip, limit=limit)


# ---- 爬虫 ----

@api_router.post("/crawler/run")
async def run_crawler(db: Session = Depends(get_db)):
    scraper = NewsScraper()
    raw_items = await scraper.fetch_all()
    pipeline = CleaningPipeline()
    articles = pipeline.clean(raw_items)

    # 查询已有 external_id 集合，用于增量去重
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
        # 数据质量校验：跳过缺失关键字段或风险等级异常的条目
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

    # 选择性分析高/极高风险条目（最多 5 条）
    analyzed = 0
    service = SentimentService(db)
    high_risk = [a for a in articles if a.risk_level in ("高", "极高")][:5]
    for article in high_risk:
        try:
            service.analyze(text=article.cleaned_content[:2000], source=article.source_name)
            analyzed += 1
        except Exception:
            pass

    # 记录采集日志
    status = crawler_get_status()
    db.add(CrawlerLog(
        fetched=len(raw_items),
        cleaned=len(articles),
        persisted=persisted,
        deduped=deduped,
        sources_ok=",".join(status.get("sources_ok", [])),
        sources_failed=",".join(status.get("sources_failed", [])),
    ))
    db.commit()

    return {
        "fetched": len(raw_items),
        "cleaned": len(articles),
        "persisted": persisted,
        "deduped": deduped,
        "analyzed": analyzed,
        "status": status,
    }


@api_router.get("/crawler/status")
def crawler_status():
    return crawler_get_status()


# ---- 效果评估 ----

@api_router.post("/evaluation/ab-test")
def run_ab_test(req: AbTestRequest, db: Session = Depends(get_db)):
    service = EvaluationService(db)
    return service.run_ab_test(dataset=req.dataset, agent_type=req.agent_type)


@api_router.get("/evaluation/metrics")
def get_metrics(db: Session = Depends(get_db)):
    service = EvaluationService(db)
    return service.compute_overall_metrics()


@api_router.get("/llm/status")
def get_llm_status() -> dict[str, Any]:
    """Return non-sensitive LLM configuration status for the frontend."""
    settings = get_settings()
    if settings.use_local_llm:
        return {
            "enabled": True,
            "mode": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
            "is_fallback": False,
        }
    if settings.openai_api_key and len(settings.openai_api_key) > 7:
        return {
            "enabled": True,
            "mode": "openai",
            "model": settings.openai_model,
            "base_url": settings.openai_base_url,
            "is_fallback": False,
        }
    return {
        "enabled": False,
        "mode": "fallback",
        "model": "规则引擎",
        "base_url": "",
        "is_fallback": True,
    }


# ---- 分析历史记录 ----

@api_router.get("/analysis/history")
def list_analysis_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(AnalysisHistory).count()
    items = (
        db.query(AnalysisHistory)
        .order_by(AnalysisHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": h.id,
                "text": h.text[:200],
                "risk_level": h.risk_level,
                "risk_type": h.risk_type,
                "risk_score": h.risk_score,
                "response_time_ms": h.response_time_ms,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in items
        ],
    }


@api_router.get("/analysis/history/{history_id}")
def get_analysis_history_detail(history_id: int, db: Session = Depends(get_db)):
    h = db.query(AnalysisHistory).filter(AnalysisHistory.id == history_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Analysis history not found")
    return {
        "id": h.id,
        "text": h.text,
        "scan_result": h.scan_result,
        "matched_cases": h.matched_cases,
        "enterprise": h.enterprise,
        "prediction": h.prediction,
        "governance": h.governance,
        "reasoning_chain": h.reasoning_chain,
        "risk_level": h.risk_level,
        "risk_type": h.risk_type,
        "risk_score": h.risk_score,
        "response_time_ms": h.response_time_ms,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


# ---- 高危事件实时卡片 ----

@api_router.get("/dashboard/recent-high-risk")
def recent_high_risk(db: Session = Depends(get_db)):
    events = (
        db.query(SentimentEvent)
        .filter(
            SentimentEvent.status == "processed",
            SentimentEvent.risk_level.in_(["高", "极高"]),
        )
        .order_by(SentimentEvent.created_at.desc())
        .limit(5)
        .all()
    )
    return [
        {
            "id": e.id,
            "title": e.title,
            "risk_level": e.risk_level,
            "risk_type": e.risk_type,
            "risk_score": e.risk_score,
            "source": e.source,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


# ---- 数据导出 CSV ----

@api_router.get("/sentiment/events/export/csv")
def export_events_csv(db: Session = Depends(get_db)):
    events = (
        db.query(SentimentEvent)
        .filter(SentimentEvent.status == "processed")
        .order_by(SentimentEvent.created_at.desc())
        .limit(5000)
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "标题", "来源", "风险等级", "风险类型", "风险评分", "关联企业", "时间"])
    for e in events:
        writer.writerow([
            e.id,
            e.title,
            e.source or "",
            e.risk_level or "",
            e.risk_type or "",
            e.risk_score,
            e.enterprise_name or "",
            e.created_at.isoformat() if e.created_at else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_export.csv"},
    )


# ---- 企业风险趋势 ----

@api_router.get("/enterprises/{enterprise_id}/trend")
def get_enterprise_trend(enterprise_id: int, db: Session = Depends(get_db)):
    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    now = datetime.now(UTC)
    start = now - timedelta(days=30)
    rows = (
        db.query(
            func.date(SentimentEvent.created_at).label("date"),
            func.count(SentimentEvent.id).label("count"),
            func.avg(SentimentEvent.risk_score).label("avg_score"),
        )
        .filter(
            SentimentEvent.enterprise_id == enterprise_id,
            SentimentEvent.status == "processed",
            SentimentEvent.created_at >= start,
        )
        .group_by(func.date(SentimentEvent.created_at))
        .order_by(func.date(SentimentEvent.created_at))
        .all()
    )
    return [
        {"date": str(r.date), "count": r.count, "avg_score": round(float(r.avg_score or 0), 2)}
        for r in rows
    ]


# ---- 爬虫采集日志 ----

@api_router.get("/crawler/logs")
def get_crawler_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(CrawlerLog)
        .order_by(CrawlerLog.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": log.id,
            "fetched": log.fetched,
            "cleaned": log.cleaned,
            "persisted": log.persisted,
            "deduped": log.deduped,
            "sources_ok": log.sources_ok,
            "sources_failed": log.sources_failed,
            "error": log.error,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
