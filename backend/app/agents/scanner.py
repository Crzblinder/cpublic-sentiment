import re
from typing import Any

from app.agents.base import BaseAgent


class SentimentScannerAgent(BaseAgent):
    name = "scanner"

    # Deterministic keyword-based risk lexicon for fallback / no-LLM mode
    RISK_KEYWORDS = {
        "产品质量": [
            "质量", "缺陷", "召回", "不合格", "爆炸", "起火", "漏油",
            "异响", "断轴", "自燃", "故障",
        ],
        "食品安全": [
            "食品", "过期", "添加剂", "农药残留", "吃出", "呕吐", "腹泻",
            "异物", "发霉", "变质", "拉肚子",
        ],
        "数据泄露": [
            "数据", "泄露", "隐私", "黑客", "盗号", "信息泄露",
            "用户信息", "数据库", "撞库", "勒索病毒",
        ],
        "劳资纠纷": [
            "员工", "裁员", "罢工", "欠薪", "加班", "劳动争议",
            "社保", "公积金", "仲裁", "讨薪",
        ],
        "高管丑闻": [
            "高管", "CEO", "创始人", "性侵", "贪腐", "拘留", "被捕",
            "行贿", "受贿", "落马", "失联",
        ],
        "环保处罚": [
            "污染", "排放", "环保", "处罚", "环保督察", "环评",
            "废气", "废水", "重金属",
        ],
        "虚假宣传": [
            "虚假宣传", "夸大", "广告违法", "误导", "假一赔",
            "智商税", "功效", "神医", "神药",
        ],
        "服务中断": [
            "宕机", "崩溃", "无法登录", "系统故障", "服务中断",
            "停机维护", "503", "连接超时",
        ],
        "金融违规": [
            "违规", "罚单", "证监会", "银监会", "P2P", "暴雷",
            "非法集资", "操纵股价", "内幕交易", "跑路",
        ],
        "知识产权": ["侵权", "抄袭", "盗版", "专利", "商标", "版权", "山寨", "盗用"],
        "税务问题": ["偷税", "漏税", "逃税", "税务", "欠税", "虚开发票", "税务稽查"],
    }

    POSITIVE_KEYWORDS = [
        "发布", "突破", "获奖", "增长", "盈利", "合作", "创新", "领先", "上市", "融资",
        "签约", "中标", "里程碑", "表彰", "荣登", "蝉联",
    ]
    NEGATIVE_KEYWORDS = [
        "丑闻", "曝光", "处罚", "下降", "亏损", "裁员", "暴雷", "危机", "质疑", "投诉",
        "维权", "下架", "封禁", "约谈", "立案调查", "罚款", "跌停", "崩盘", "跑路",
    ]

    HIGH_CONFIDENCE_KEYWORDS = ["监管", "处罚", "立案", "逮捕", "死亡", "爆炸", "大规模", "全国性"]
    INDUSTRY_KEYWORDS = {
        "互联网": ["平台", "App", "电商", "直播", "外卖", "网约车", "短视频", "游戏", "社交"],
        "金融": ["银行", "保险", "证券", "基金", "P2P", "贷款", "理财", "信托", "支付"],
        "食品餐饮": ["食品", "餐饮", "奶茶", "咖啡", "连锁", "零食", "餐饮", "食材"],
        "汽车": ["汽车", "新能源", "电动车", "车企", "动力电池", "充电桩", "自动驾驶"],
        "医药": ["医药", "疫苗", "医院", "医疗器械", "药品", "处方药", "临床"],
        "房地产": ["房地产", "楼盘", "物业", "开发商", "交房", "烂尾", "公摊"],
        "消费电子": ["手机", "电脑", "芯片", "半导体", "智能硬件", "屏幕", "电池"],
        "零售": ["超市", "便利店", "百货", "商场", "零售", "电商", "门店"],
        "物流": ["快递", "物流", "仓储", "配送", "供应链", "货运"],
        "能源": ["电力", "石油", "天然气", "煤炭", "新能源", "光伏", "风电"],
    }

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        text = user_prompt
        # Extract entities (simple regex for Chinese org names)
        entities = re.findall(
            r"[\u4e00-\u9fa5]{2,}"
            r"(?:公司|集团|企业|平台|银行|保险|证券|基金|酒店|餐饮|科技|汽车|医药|地产|航空|物流|电商)",
            text,
        )
        entities = list(set(entities))[:5]

        risk_type = "其他"
        confidence = 0.5
        matched_keywords: list[str] = []
        for rt, keywords in self.RISK_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in text]
            if hits:
                risk_type = rt
                matched_keywords = hits
                confidence = 0.75
                break

        sentiment = "中性"
        positive_hits = [kw for kw in self.POSITIVE_KEYWORDS if kw in text]
        negative_hits = [kw for kw in self.NEGATIVE_KEYWORDS if kw in text]
        if positive_hits and not negative_hits and risk_type == "其他":
            sentiment = "正面"
            confidence = max(confidence, 0.7)
        if negative_hits or risk_type != "其他":
            sentiment = "负面"
            confidence = max(confidence, 0.8)

        # Boost confidence when strong authoritative signals appear
        if any(kw in text for kw in self.HIGH_CONFIDENCE_KEYWORDS):
            confidence = min(0.95, confidence + 0.1)

        relevant = bool(entities) and (risk_type != "其他" or sentiment == "负面")

        return {
            "relevant": relevant,
            "industry": self._guess_industry(text),
            "risk_type": risk_type,
            "sentiment": sentiment,
            "confidence": round(min(confidence, 0.95), 2),
            "entities": entities,
            "matched_keywords": matched_keywords or negative_hits or positive_hits,
            "simulated": True,
            "_latency_ms": 5,
        }

    def _guess_industry(self, text: str) -> str:
        scores: dict[str, int] = {}
        for industry, kws in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in kws if kw in text)
            if score:
                scores[industry] = score
        if not scores:
            return "综合"
        return max(scores, key=scores.get)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        text = context.get("text", "")
        system_prompt = self._load_prompt()
        user_prompt = f"文本：{text}"
        result = self.call_llm(system_prompt, user_prompt)
        result["agent"] = self.name
        result["prompt_variant"] = self.prompt_variant
        return result
