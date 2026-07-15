from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts import PROMPT_VARIANTS


class RiskPredictorAgent(BaseAgent):
    name = "predictor"

    def _get_prompt(self) -> str:
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["name"] == self.prompt_variant:
                return variant["template"]
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["is_baseline"]:
                return variant["template"]
        raise ValueError(f"No prompt variant found for {self.name}")

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        import re

        text = user_prompt
        risk_level = "低"
        risk_score = 0.2

        high_signals = ["广泛传播", "监管", "处罚", "曝光", "丑闻", " arrested", "跌停"]
        mid_signals = ["投诉", "争议", "质疑", "负面", "裁员"]

        if any(s in text for s in high_signals):
            risk_level = "高"
            risk_score = 0.8
        elif any(s in text for s in mid_signals):
            risk_level = "中"
            risk_score = 0.55

        # Adjust by enterprise scale hint
        if "大型" in text or "百亿" in text or "千亿" in text:
            risk_score = min(0.95, risk_score + 0.05)

        # Extract risk type from scanner hint if present
        risk_type_match = re.search(r"风险类型[：:]\s*([^\n，。]+)", text)
        risk_type = risk_type_match.group(1).strip() if risk_type_match else "经营风险"

        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 2),
            "risk_type": risk_type,
            "time_horizon": "7-14天" if risk_level in ["高", "极高"] else "14-30天",
            "key_indicators": ["社交媒体传播", "监管介入", "消费者投诉"][:3],
            "simulated": True,
            "_latency_ms": 5,
        }

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        sentiment_text = context.get("sentiment_text", "")
        case_summary = context.get("case_summary", "无匹配案例")
        enterprise_profile = context.get("enterprise_profile", "无企业画像")
        system_prompt = self._get_prompt()
        user_prompt = (
            system_prompt.replace("{sentiment_text}", sentiment_text)
            .replace("{case_summary}", case_summary)
            .replace("{enterprise_profile}", enterprise_profile)
        )
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
