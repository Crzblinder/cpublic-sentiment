from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import AbTestRequest, EventResponse, LabelRequest, SentimentAnalyzeRequest
from app.models.base import get_db
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.models.sentiment import SentimentEvent
from app.services.evaluation_service import EvaluationService
from app.services.sentiment_service import SentimentService

api_router = APIRouter()


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


@api_router.get("/sentiment/events", response_model=list[EventResponse])
def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = SentimentService(db)
    events = service.list_events(skip=skip, limit=limit)
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


@api_router.get("/cases")
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    industry: str | None = None,
    risk_type: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(RiskCase)
    if industry:
        q = q.filter(RiskCase.industry == industry)
    if risk_type:
        q = q.filter(RiskCase.risk_type == risk_type)
    cases = q.order_by(RiskCase.id.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "industry": c.industry,
            "risk_type": c.risk_type,
            "risk_level": c.risk_level,
            "summary": c.summary[:200],
        }
        for c in cases
    ]


@api_router.get("/enterprises")
def list_enterprises(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    industry: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Enterprise)
    if industry:
        q = q.filter(Enterprise.industry == industry)
    enterprises = q.offset(skip).limit(limit).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "industry": e.industry,
            "scale": e.scale,
            "region": e.region,
        }
        for e in enterprises
    ]


@api_router.post("/evaluation/ab-test")
def run_ab_test(req: AbTestRequest, db: Session = Depends(get_db)):
    service = EvaluationService(db)
    return service.run_ab_test(dataset=req.dataset, agent_type=req.agent_type)


@api_router.get("/evaluation/metrics")
def get_metrics(db: Session = Depends(get_db)):
    service = EvaluationService(db)
    return service.compute_overall_metrics()
