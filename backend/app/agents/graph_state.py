"""LangGraph 工作流全局状态定义。

每个图节点接收 SentimentState，返回 Partial[SentimentState] 增量更新。
"""

from __future__ import annotations

from typing import Any, TypedDict


class SentimentState(TypedDict, total=False):
    """舆情分析 LangGraph 工作流的全局状态。

    total=False 表示所有字段均为可选，允许节点仅填充所需字段。
    """

    # ---- 输入（由调用方初始化） ----
    text: str
    enterprise_hint: str | None
    prompt_variants: dict[str, str] | None

    # ---- 各节点输出 ----
    scan_result: dict[str, Any] | None
    candidate_cases: list[dict[str, Any]] | None
    matched_cases: list[dict[str, Any]] | None
    enterprise: dict[str, Any] | None
    prediction: dict[str, Any] | None
    governance: dict[str, Any] | None
    expert_review: dict[str, Any] | None

    # ---- 元数据 ----
    reasoning_chain: list[dict[str, Any]]
    route_decision: str | None  # "normal" / "fast_exit" / "expert_review"
    response_time_ms: int
    stream_events: list[dict[str, Any]]
