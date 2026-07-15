import re
from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts import PROMPT_VARIANTS


class SentimentScannerAgent(BaseAgent):
    name = "scanner"

    # Deterministic keyword-based risk lexicon for fallback / no-LLM mode
    RISK_KEYWORDS = {
        "产品质量": ["质量", "缺陷", "召回", "不合格", "爆炸", "起火", "漏油"],
        "食品安全": ["食品", "过期", "添加剂", "农药残留", "吃出", "呕吐", "腹泻"],
        "数据泄露": ["数据", "泄露", "隐私", "黑客", "盗号", "信息泄露"],
        "劳资纠纷": ["员工", "裁员", "罢工", "欠薪", "加班", "劳动争议"],
        "高管丑闻": ["高管", "CEO", "创始人", "性侵", "贪腐", "拘留", "被捕"],
        "环保处罚": ["污染", "排放", "环保", "处罚", "环保督察"],
        "虚假宣传": ["虚假宣传", "夸大", "广告违法", "误导", "假一赔"],
        "服务中断": ["宕机", "崩溃", "无法登录", "系统故障", "服务中断"],
        "金融违规": ["违规", "罚单", "证监会", "银监会", "P2P", "暴雷"],
    }

    POSITIVE_KEYWORDS = ["发布", "突破", "获奖", "增长", "盈利", "合作", "创新", "领先"]
    NEGATIVE_KEYWORDS = ["丑闻", "曝光", "处罚", "下降", "亏损", "裁员", "暴雷", "危机"]

    def _get_prompt(self) -> str:
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["name"] == self.prompt_variant:
                return variant["template"]
        # Default
        for variant in PROMPT_VARIANTS:
            if variant["agent_type"] == self.name and variant["is_baseline"]:
                return variant["template"]
        raise ValueError(f"No prompt variant found for {self.name}")

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        text = user_prompt
        # Extract entities (simple regex for Chinese org names)
        entities = re.findall(
            r"[\u4e00-\u9fa5]{2,}"
            r"(?:公司|集团|企业|平台|银行|保险|证券|基金|酒店|餐饮|科技)",
            text,
        )
        entities = list(set(entities))[:5]

        risk_type = "其他"
        confidence = 0.5
        for rt, keywords in self.RISK_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                risk_type = rt
                confidence = 0.75
                break

        sentiment = "中性"
        if any(kw in text for kw in self.POSITIVE_KEYWORDS):
            sentiment = "正面"
            confidence = max(confidence, 0.7)
        if any(kw in text for kw in self.NEGATIVE_KEYWORDS) or risk_type != "其他":
            sentiment = "负面"
            confidence = max(confidence, 0.8)

        relevant = bool(entities) and (risk_type != "其他" or sentiment == "负面")

        return {
            "relevant": relevant,
            "industry": self._guess_industry(text),
            "risk_type": risk_type,
            "sentiment": sentiment,
            "confidence": round(min(confidence, 0.95), 2),
            "entities": entities,
            "simulated": True,
            "_latency_ms": 5,
        }

    def _guess_industry(self, text: str) -> str:
        industry_map = {
            "互联网": ["平台", "App", "电商", "直播", "外卖", "网约车"],
            "金融": ["银行", "保险", "证券", "基金", "P2P", "贷款"],
            "食品餐饮": ["食品", "餐饮", "奶茶", "咖啡", "连锁"],
            "汽车": ["汽车", "新能源", "电动车", "车企"],
            "医药": ["医药", "疫苗", "医院", "医疗器械"],
            "房地产": ["房地产", "楼盘", "物业", "开发商"],
        }
        for industry, kws in industry_map.items():
            if any(kw in text for kw in kws):
                return industry
        return "综合"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        text = context.get("text", "")
        user_prompt = f"文本：{text}"
        system_prompt = self._get_prompt()
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
