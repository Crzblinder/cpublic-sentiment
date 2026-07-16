from typing import Any

from app.agents.base import BaseAgent


class GovernanceAgent(BaseAgent):
    name = "governance"

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        risk_level = "中"
        if "高" in user_prompt or "极高" in user_prompt:
            risk_level = "高"
        elif "低" in user_prompt:
            risk_level = "低"

        if risk_level == "高":
            immediate = ["高管致歉声明", "成立专项组", "暂停相关业务"]
            short_term = ["第三方调查", "发布整改方案", "用户补偿"]
            long_term = ["制度流程重塑", "合规培训常态化"]
            cost = "100-500 万元"
        elif risk_level == "中":
            immediate = ["监测舆情传播", "内部核实", "准备回应口径"]
            short_term = ["发布说明公告", "优化相关产品/服务"]
            long_term = ["建立预警机制"]
            cost = "10-50 万元"
        else:
            immediate = ["持续监测"]
            short_term = ["例行回应"]
            long_term = ["维护品牌声誉"]
            cost = "1-5 万元"

        return {
            "immediate_actions": immediate,
            "short_term_actions": short_term,
            "long_term_actions": long_term,
            "spokesperson_message": "公司高度重视，正在积极核实并妥善处理。",
            "monitoring_plan": ["7x24 小时舆情监测", "日报/周报输出"],
            "estimated_cost": cost,
            "simulated": True,
            "_latency_ms": 5,
        }

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        sentiment_text = context.get("sentiment_text", "")
        risk_level = context.get("risk_level", "中")
        playbook = context.get("playbook", "")
        template = self._load_prompt()
        system_prompt = template
        user_prompt = (
            template.replace("{sentiment_text}", sentiment_text)
            .replace("{risk_level}", risk_level)
            .replace("{playbook}", playbook)
        )
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
