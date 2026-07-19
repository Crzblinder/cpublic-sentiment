"""LangGraph 舆情分析工作流构建与编译。

使用 StateGraph 定义有向图：
  scan → route → [normal: retrieve→match→predict→govern | fast_exit | expert_review→govern_urgent]
  → finalize → END

提供:
  - build_sentiment_graph(): 构建并编译图
  - run_analysis(): 同步执行分析的便捷接口
  - run_analysis_stream(): 异步流式执行（用于 SSE）
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.graph_nodes import build_nodes
from app.agents.graph_state import SentimentState
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)


def build_sentiment_graph(
    db: Session,
    prompt_variants: dict[str, str] | None = None,
):
    """构建并编译舆情分析 LangGraph 工作流。"""
    nodes = build_nodes(db, prompt_variants=prompt_variants)

    graph = StateGraph(SentimentState)

    # 添加节点
    graph.add_node("scan", nodes["scan"])
    graph.add_node("retrieve", nodes["retrieve"])
    graph.add_node("match", nodes["match"])
    graph.add_node("predict", nodes["predict"])
    graph.add_node("govern", nodes["govern"])
    graph.add_node("govern_urgent", nodes["govern_urgent"])
    graph.add_node("expert_review", nodes["expert_review"])
    graph.add_node("finalize", nodes["finalize"])
    graph.add_node("fast_exit", nodes["fast_exit"])

    # 边定义
    graph.add_edge(START, "scan")

    # 条件路由：scan 之后根据结果分流
    graph.add_conditional_edges(
        "scan",
        nodes["_route_scan"],
        {
            "normal": "retrieve",
            "fast_exit": "fast_exit",
            "expert_review": "expert_review",
        },
    )

    # 正常路径
    graph.add_edge("retrieve", "match")
    graph.add_edge("match", "predict")
    graph.add_edge("predict", "govern")
    graph.add_edge("govern", "finalize")

    # 快速通道
    graph.add_edge("fast_exit", "finalize")

    # 专家审核路径
    graph.add_edge("expert_review", "govern_urgent")
    graph.add_edge("govern_urgent", "finalize")

    # 所有路径汇入 finalize → END
    graph.add_edge("finalize", END)

    return graph.compile()


def run_analysis(
    db: Session,
    text: str,
    enterprise_hint: str | None = None,
    prompt_variants: dict[str, str] | None = None,
) -> dict[str, Any]:
    """同步执行舆情分析，返回与旧 Orchestrator 兼容的结果字典。"""
    start_time = time.time()

    graph = build_sentiment_graph(db, prompt_variants=prompt_variants)

    initial_state: SentimentState = {
        "text": text,
        "enterprise_hint": enterprise_hint,
        "prompt_variants": prompt_variants,
        "reasoning_chain": [],
        "stream_events": [],
    }

    final_state = graph.invoke(initial_state)
    elapsed_ms = int((time.time() - start_time) * 1000)

    return _format_result(final_state, elapsed_ms, prompt_variants)


async def run_analysis_stream(
    db: Session,
    text: str,
    enterprise_hint: str | None = None,
    prompt_variants: dict[str, str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """异步流式执行舆情分析，逐步 yield 每个节点的结果更新。

    通过累加所有节点更新得到最终状态，避免再调用一次 graph.invoke 造成重复执行。
    """
    start_time = time.time()

    graph = build_sentiment_graph(db, prompt_variants=prompt_variants)

    initial_state: SentimentState = {
        "text": text,
        "enterprise_hint": enterprise_hint,
        "prompt_variants": prompt_variants,
        "reasoning_chain": [],
        "stream_events": [],
    }

    # 累加各节点更新以获得最终状态，避免额外 invoke
    running_state: dict[str, Any] = dict(initial_state)

    async for event in graph.astream(initial_state, stream_mode="updates"):
        for update in event.values():
            if isinstance(update, dict):
                running_state.update(update)
        elapsed_ms = int((time.time() - start_time) * 1000)
        yield {
            "node_update": event,
            "elapsed_ms": elapsed_ms,
        }

    # 最终完整结果直接从累加状态生成
    elapsed_ms = int((time.time() - start_time) * 1000)
    yield {
        "final_result": _format_result(running_state, elapsed_ms, prompt_variants),
        "elapsed_ms": elapsed_ms,
    }


def persist_event(db: Session, text: str, result: dict[str, Any], source: str = "manual") -> int:
    """将分析结果持久化到 SentimentEvent，返回 event_id。"""
    event = SentimentEvent(
        title=text[:120],
        content=text,
        source=source,
        enterprise_name=(
            result.get("enterprise", {}).get("name") if result.get("enterprise") else None
        ),
        risk_level=result["prediction"].get("risk_level"),
        risk_type=result["prediction"].get("risk_type"),
        risk_score=result["prediction"].get("risk_score", 0.0),
        matched_case_ids=[c["id"] for c in result.get("matched_cases", [])],
        governance_plan=result.get("governance"),
        reasoning_chain=result.get("reasoning_chain", []),
        response_time_ms=result.get("response_time_ms", 0),
        prompt_variant=(result.get("prompt_variants") or {}).get("scanner"),
        status="processed",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event.id


def _format_result(
    state: SentimentState,
    elapsed_ms: int,
    prompt_variants: dict[str, str] | None,
) -> dict[str, Any]:
    """将最终 State 转换为与旧 Orchestrator 兼容的结果格式。"""
    matched_cases = state.get("matched_cases") or []
    enterprise = state.get("enterprise")

    return {
        "text": state.get("text", ""),
        "scan": state.get("scan_result") or {},
        "matched_cases": [
            {
                "id": c["id"],
                "title": c["title"],
                "risk_level": c["risk_level"],
                "risk_type": c["risk_type"],
            }
            for c in matched_cases
        ],
        "enterprise": (
            {"id": enterprise["id"], "name": enterprise["name"], "industry": enterprise["industry"]}
            if enterprise
            else None
        ),
        "prediction": state.get("prediction") or {},
        "governance": state.get("governance") or {},
        "expert_review": state.get("expert_review"),
        "reasoning_chain": state.get("reasoning_chain") or [],
        "route_decision": state.get("route_decision") or "normal",
        "stream_events": state.get("stream_events") or [],
        "response_time_ms": elapsed_ms,
        "prompt_variants": prompt_variants or {},
    }
