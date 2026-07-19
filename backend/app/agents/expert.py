"""专家审核 Agent — 对极高危事件进行综合风控评估。

当路由判定为 expert_review 时触发，综合 Scanner 输出、预测结果，
给出审核意见、是否需要升级处理、建议时间线。
"""

from typing import Any

from app.agents.base import BaseAgent


class ExpertReviewAgent(BaseAgent):
    name = "expert"

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """无 LLM 时的确定性降级。"""
        text = user_prompt
        high_signals = ["暴雷", "监管", "重大", "死亡", "逮捕", "破产"]
        critical_count = sum(1 for s in high_signals if s in text)

        escalation = critical_count >= 2
        timeline = "立即（24小时内）" if escalation else "48小时内"

        return {
            "review_opinion": "事件涉及重大风险信号，建议启动应急响应机制。",
            "escalation_required": escalation,
            "recommended_timeline": timeline,
            "key_risks": [s for s in high_signals if s in text] or ["综合风险"],
            "confidence_level": "high" if escalation else "medium",
            "simulated": True,
            "_latency_ms": 5,
        }

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        text = context.get("sentiment_text", "")
        scan_result = context.get("scan_result", {})
        prediction = context.get("prediction", {})

        template = self._load_prompt()
        system_prompt = template
        user_prompt = (
            template
            .replace("{sentiment_text}", text)
            .replace("{scan_result}", str(scan_result))
            .replace("{prediction}", str(prediction))
        )
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
