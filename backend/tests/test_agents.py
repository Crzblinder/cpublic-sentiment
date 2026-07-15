import os

from app.agents.governance import GovernanceAgent
from app.agents.matcher import CaseMatcherAgent
from app.agents.predictor import RiskPredictorAgent
from app.agents.scanner import SentimentScannerAgent

os.environ.setdefault("OPENAI_API_KEY", "")


def test_scanner_fallback():
    agent = SentimentScannerAgent()
    result = agent.run({"text": "某食品公司被曝使用过期原料，引发消费者投诉。"})
    assert result["agent"] == "scanner"
    assert result["relevant"] is True
    assert result["risk_type"] == "食品安全"
    assert result["sentiment"] == "负面"


def test_matcher_fallback():
    agent = CaseMatcherAgent()
    cases = [
        {
            "id": 1,
            "title": "食品过期案例",
            "summary": "某公司食品过期被处罚",
            "industry": "食品餐饮",
            "risk_type": "食品安全",
        },
        {
            "id": 2,
            "title": "数据泄露案例",
            "summary": "某公司数据库泄露",
            "industry": "互联网",
            "risk_type": "数据泄露",
        },
    ]
    result = agent.run({"sentiment_text": "某食品公司被曝使用过期原料", "candidate_cases": cases})
    assert result["agent"] == "matcher"
    assert 1 in result["matched_case_ids"]


def test_predictor_fallback():
    agent = RiskPredictorAgent()
    result = agent.run({"sentiment_text": "某企业被监管部门处罚，舆论广泛传播"})
    assert result["agent"] == "predictor"
    assert result["risk_level"] in ["低", "中", "高", "极高"]
    assert 0 <= result["risk_score"] <= 1


def test_governance_fallback():
    agent = GovernanceAgent()
    result = agent.run({"sentiment_text": "某企业发生重大数据泄露", "risk_level": "高"})
    assert result["agent"] == "governance"
    assert len(result["immediate_actions"]) > 0
