"""LangGraph 工作流节点函数。

每个节点函数接收 SentimentState，返回 dict 增量更新。
通过 build_nodes() 工厂函数注入 DB Session 和 Agent 实例。
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agents.expert import ExpertReviewAgent
from app.agents.governance import GovernanceAgent
from app.agents.graph_state import SentimentState
from app.agents.matcher import CaseMatcherAgent
from app.agents.predictor import RiskPredictorAgent
from app.agents.scanner import SentimentScannerAgent
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# 高危信号关键词（用于条件路由）
HIGH_SIGNAL_KEYWORDS = ["暴雷", "监管", "重大", "死亡", "逮捕", "破产", "爆炸", "毒害"]


def _emit_event(
    state: SentimentState,
    step: str,
    agent: str,
    status: str = "complete",
    summary: str = "",
) -> list[dict[str, Any]]:
    """向 stream_events 追加一条事件。"""
    events = list(state.get("stream_events") or [])
    events.append({
        "step": step,
        "agent": agent,
        "status": status,
        "output_summary": summary,
    })
    return events


def build_nodes(
    db: Session,
    prompt_variants: dict[str, str] | None = None,
) -> dict[str, Any]:
    """构建所有节点函数，返回 {node_name: callable} 字典。

    DB Session、Agent 实例和 Retriever 通过闭包捕获，
    避免将不可序列化对象放入 State。
    """
    pv = prompt_variants or {}
    retriever = HybridRetriever(db)
    scanner = SentimentScannerAgent(prompt_variant=pv.get("scanner"))
    matcher = CaseMatcherAgent(prompt_variant=pv.get("matcher"))
    predictor = RiskPredictorAgent(prompt_variant=pv.get("predictor"))
    governance = GovernanceAgent(prompt_variant=pv.get("governance"))
    expert = ExpertReviewAgent(prompt_variant=pv.get("expert"))

    # ------------------------------------------------------------------
    # 节点：scan
    # ------------------------------------------------------------------
    def scan_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        result = scanner.run({"text": text})
        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "scan", "agent": "scanner", "output": result})
        summary = f"风险类型={result.get('risk_type')}, 置信度={result.get('confidence')}"
        return {
            "scan_result": result,
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "scan", "scanner", summary=summary),
        }

    # ------------------------------------------------------------------
    # 条件路由：route_scan
    # ------------------------------------------------------------------
    def route_scan(state: SentimentState) -> str:
        scan = state.get("scan_result") or {}
        confidence = scan.get("confidence", 0.5)
        risk_type = scan.get("risk_type", "其他")
        text = state.get("text", "")

        # 低置信度 + 非核心风险类型 -> 快速通道
        if confidence < 0.3 and risk_type == "其他":
            return "fast_exit"

        # 包含高危信号 -> 专家审核
        if any(s in text for s in HIGH_SIGNAL_KEYWORDS):
            return "expert_review"

        return "normal"

    # ------------------------------------------------------------------
    # 节点：retrieve（RAG 检索 + 企业匹配）
    # ------------------------------------------------------------------
    def retrieve_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        scan = state.get("scan_result") or {}
        hint = state.get("enterprise_hint")

        industry = scan.get("industry", "")
        risk_type = scan.get("risk_type", "")
        entities = scan.get("entities", [])

        # RAG 检索候选案例
        candidate_cases = retriever.retrieve_cases(
            query=text,
            industry=industry if industry else None,
            risk_type=risk_type if risk_type else None,
            top_k=5,
        )

        # 匹配企业
        enterprise = _match_enterprise(db, hint, entities)
        ent_dict = None
        if enterprise:
            ent_dict = {
                "id": enterprise.id,
                "name": enterprise.name,
                "industry": enterprise.industry,
                "scale": enterprise.scale,
                "region": enterprise.region,
                "business_tags": enterprise.business_tags or [],
                "risk_profile": enterprise.risk_profile or {},
            }

        summary = f"候选案例={len(candidate_cases)}, 企业={'已匹配' if ent_dict else '无'}"
        return {
            "candidate_cases": candidate_cases,
            "enterprise": ent_dict,
            "stream_events": _emit_event(state, "retrieve", "rag", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：match
    # ------------------------------------------------------------------
    def match_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        candidate_cases = state.get("candidate_cases") or []

        result = matcher.run({
            "sentiment_text": text,
            "candidate_cases": candidate_cases,
        })

        matched_ids = result.get("matched_case_ids", [])
        matched_cases = (
            [
                {"id": c.id, "title": c.title, "risk_level": c.risk_level, "risk_type": c.risk_type,
                 "summary": c.summary, "governance_playbook": c.governance_playbook}
                for c in db.query(RiskCase).filter(RiskCase.id.in_(matched_ids)).all()
            ]
            if matched_ids
            else []
        )

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "match", "agent": "matcher", "output": result})

        summary = f"匹配案例={len(matched_cases)}"
        return {
            "matched_cases": matched_cases,
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "match", "matcher", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：predict
    # ------------------------------------------------------------------
    def predict_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        matched_cases = state.get("matched_cases") or []
        enterprise = state.get("enterprise")

        case_summary = "\n".join(
            f"{c['title']}（{c['risk_type']}，{c['risk_level']}）: {c.get('summary', '')}"
            for c in matched_cases
        ) or "无匹配案例"

        if enterprise:
            tags = ", ".join(enterprise.get("business_tags", []))
            enterprise_profile = (
                f"企业：{enterprise['name']}，行业：{enterprise['industry']}，"
                f"规模：{enterprise.get('scale', '')}，地区：{enterprise.get('region', '')}，"
                f"业务标签：{tags}，风险画像：{enterprise.get('risk_profile', {})}"
            )
        else:
            enterprise_profile = "无企业画像"

        result = predictor.run({
            "sentiment_text": text,
            "case_summary": case_summary,
            "enterprise_profile": enterprise_profile,
        })

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "predict", "agent": "predictor", "output": result})

        summary = f"风险等级={result.get('risk_level')}, 评分={result.get('risk_score')}"
        return {
            "prediction": result,
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "predict", "predictor", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：govern（标准模式）
    # ------------------------------------------------------------------
    def govern_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        prediction = state.get("prediction") or {}
        matched_cases = state.get("matched_cases") or []
        risk_level = prediction.get("risk_level", "中")

        playbook = "\n".join(
            f"{c['title']}: {c.get('governance_playbook', {}).get('summary', '无')}"
            for c in matched_cases
            if c.get("governance_playbook")
        )

        result = governance.run({
            "sentiment_text": text,
            "risk_level": risk_level,
            "playbook": playbook,
        })

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "govern", "agent": "governance", "output": result})

        summary = f"即时行动={len(result.get('immediate_actions', []))}项"
        return {
            "governance": result,
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "govern", "governance", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：govern_urgent（紧急模式 — 注入更高优先级）
    # ------------------------------------------------------------------
    def govern_urgent_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        expert_review = state.get("expert_review") or {}
        prediction = state.get("prediction") or {}
        risk_level = prediction.get("risk_level", "极高")

        # 紧急模式：将专家审核意见作为 playbook 注入
        playbook = f"[紧急模式] 专家审核意见：{expert_review.get('review_opinion', '')}\n"
        playbook += f"建议时间线：{expert_review.get('recommended_timeline', '立即')}\n"
        if expert_review.get("key_risks"):
            playbook += f"关键风险：{', '.join(expert_review['key_risks'])}\n"

        result = governance.run({
            "sentiment_text": text,
            "risk_level": risk_level,
            "playbook": playbook,
        })

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "govern_urgent", "agent": "governance", "output": result})

        summary = f"紧急治理方案，即时行动={len(result.get('immediate_actions', []))}项"
        return {
            "governance": result,
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "govern", "governance", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：expert_review
    # ------------------------------------------------------------------
    def expert_review_node(state: SentimentState) -> dict[str, Any]:
        text = state.get("text", "")
        scan_result = state.get("scan_result") or {}

        # 专家审核在 predict 之前，所以先做一个快速预测供专家参考
        quick_pred = predictor.run({
            "sentiment_text": text,
            "case_summary": "专家审核模式 — 尚未匹配案例",
            "enterprise_profile": "无企业画像",
        })

        result = expert.run({
            "sentiment_text": text,
            "scan_result": scan_result,
            "prediction": quick_pred,
        })

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "expert_review", "agent": "expert", "output": result})

        summary = f"审核意见={result.get('review_opinion', '')[:30]}..."
        return {
            "expert_review": result,
            "prediction": quick_pred,  # 保存快速预测供后续使用
            "reasoning_chain": chain,
            "stream_events": _emit_event(state, "expert_review", "expert", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：fast_exit（快速通道 — 低置信度）
    # ------------------------------------------------------------------
    def fast_exit_node(state: SentimentState) -> dict[str, Any]:
        scan = state.get("scan_result") or {}

        # 生成轻量治理方案
        result = governance.run({
            "sentiment_text": state.get("text", ""),
            "risk_level": "低",
            "playbook": "快速通道：事件相关度较低，建议持续监测即可。",
        })

        prediction = {
            "risk_level": "低",
            "risk_score": round(scan.get("confidence", 0.2), 2),
            "risk_type": scan.get("risk_type", "其他"),
            "time_horizon": "持续监测",
            "key_indicators": ["社交媒体提及量"],
            "simulated": True,
        }

        chain = list(state.get("reasoning_chain") or [])
        chain.append({"step": "fast_exit", "agent": "governance", "output": result})

        summary = "快速通道 — 低置信度，轻量治理"
        return {
            "prediction": prediction,
            "governance": result,
            "matched_cases": [],
            "reasoning_chain": chain,
            "route_decision": "fast_exit",
            "stream_events": _emit_event(state, "fast_exit", "governance", summary=summary),
        }

    # ------------------------------------------------------------------
    # 节点：finalize
    # ------------------------------------------------------------------
    def finalize_node(state: SentimentState) -> dict[str, Any]:
        # 记录路由决策
        route = state.get("route_decision") or "normal"

        # finalize 流式事件
        summary = f"路由={route}, 完成所有分析"
        events = _emit_event(state, "finalize", "orchestrator", summary=summary)

        return {
            "route_decision": route,
            "stream_events": events,
        }

    # 返回所有节点 + 路由函数
    return {
        "scan": scan_node,
        "retrieve": retrieve_node,
        "match": match_node,
        "predict": predict_node,
        "govern": govern_node,
        "govern_urgent": govern_urgent_node,
        "expert_review": expert_review_node,
        "finalize": finalize_node,
        "fast_exit": fast_exit_node,
        # 路由函数（非节点，供 StateGraph.add_conditional_edges 使用）
        "_route_scan": route_scan,
    }


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------
def _match_enterprise(
    db: Session, hint: str | None, entities: list[str]
) -> Enterprise | None:
    """根据提示或实体列表匹配企业。"""
    if hint:
        ent = db.query(Enterprise).filter(Enterprise.name.contains(hint)).first()
        if ent:
            return ent
    for entity in entities:
        ent = db.query(Enterprise).filter(Enterprise.name.contains(entity)).first()
        if ent:
            return ent
    return None
