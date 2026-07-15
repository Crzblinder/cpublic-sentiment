import re
from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts import PROMPT_VARIANTS


class CaseMatcherAgent(BaseAgent):
    name = "matcher"

    def _get_prompt(self) -> str:
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["name"] == self.prompt_variant:
                return variant["template"]
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["is_baseline"]:
                return variant["template"]
        raise ValueError(f"No prompt variant found for {self.name}")

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        # Deterministic fallback: use simple keyword overlap scoring
        sentiment_text = user_prompt.split("舆情：")[-1].split("\n候选案例：")[0]
        sentiment_words = set(sentiment_text)

        # Parse case blocks from the rendered prompt; each block looks like:
        # - <title>（行业：...，风险类型：...，ID: N）
        #   <summary>
        scores = []
        for block in re.split(r"\n(?=- )", user_prompt.split("\n候选案例：\n")[-1]):
            id_match = re.search(r"ID:\s*(\d+)[）)]", block)
            if not id_match:
                continue
            cid = int(id_match.group(1))
            case_text = block.strip()
            overlap = sum(1 for ch in case_text if ch in sentiment_words)
            score = min(0.95, 0.3 + overlap / max(len(sentiment_text), 1))
            scores.append(
                {"case_id": cid, "score": round(score, 2), "reason": "关键词重叠（fallback）"}
            )

        scores.sort(key=lambda x: x["score"], reverse=True)
        matched = [s["case_id"] for s in scores if s["score"] > 0.5]
        return {
            "matched_case_ids": (
                matched[:3] if matched else [scores[0]["case_id"]] if scores else []
            ),
            "match_scores": scores[:5],
            "synthesis": "基于关键词重叠的确定性匹配（LLM 未配置）",
            "simulated": True,
            "_latency_ms": 5,
        }

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        sentiment_text = context.get("sentiment_text", "")
        cases = context.get("candidate_cases", [])
        cases_text = "\n".join(
            f"- {c['title']}（行业：{c['industry']}，"
            f"风险类型：{c['risk_type']}，ID: {c['id']}）\n  {c['summary']}"
            for c in cases
        )
        system_prompt = self._get_prompt()
        user_prompt = (
            system_prompt.replace("{sentiment_text}", sentiment_text)
            .replace("{cases_text}", cases_text)
        )
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
