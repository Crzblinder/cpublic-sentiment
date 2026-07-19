import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import AbTestRequest, EventResponse, LabelRequest, SentimentAnalyzeRequest
from app.crawler.scraper import NewsScraper
from app.crawler.scraper import get_status as crawler_get_status
from app.models.base import get_db
from app.models.case import RiskCase
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
        q = q.filter(RiskCase.title.contains(search))
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
    items = await scraper.fetch_all()
    # 自动分析采集到的文本
    analyzed = 0
    service = SentimentService(db)
    for item in items[:10]:  # 每次最多分析 10 条
        try:
            text = item.get("content", item.get("title", ""))
            if len(text) >= 10:
                service.analyze(text=text[:2000], source=item.get("source", "crawler"))
                analyzed += 1
        except Exception:
            pass
    return {
        "fetched": len(items),
        "analyzed": analyzed,
        "status": crawler_get_status(),
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
