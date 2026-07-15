"""Insert a small deterministic dataset for smoke tests.

This avoids downloading the embedding model; the full seed script remains
backend/scripts/seed_data.py for production-like workloads.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.base import SessionLocal
from app.models.case import RiskCase
from app.models.enterprise import Enterprise


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Enterprise).count() == 0:
            enterprises = [
                Enterprise(name="示例科技", industry="互联网", scale="大型", region="北京", business_tags=["SaaS", "云计算"]),
                Enterprise(name="示例食品", industry="食品餐饮", scale="中型", region="上海", business_tags=["速冻食品", "冷链物流"]),
                Enterprise(name="示例出行", industry="交通运输", scale="大型", region="深圳", business_tags=["网约车", "共享出行"]),
            ]
            db.add_all(enterprises)
            db.flush()

        if db.query(RiskCase).count() == 0:
            cases = [
                RiskCase(title="数据泄露处罚", industry="互联网", risk_type="数据泄露", risk_level="高", summary="某科技公司数据库泄露，被监管部门处罚。"),
                RiskCase(title="食品过期事件", industry="食品餐饮", risk_type="食品安全", risk_level="高", summary="某食品企业使用过期原料，引发舆论危机。"),
                RiskCase(title="骑手配送纠纷", industry="互联网", risk_type="劳资纠纷", risk_level="中", summary="外卖骑手与消费者发生冲突，视频在社交平台传播。"),
                RiskCase(title="App大规模宕机", industry="互联网", risk_type="服务中断", risk_level="高", summary="某科技公司App无法登录，用户投诉激增。"),
            ]
            db.add_all(cases)

        db.commit()
        print(f"Minimal seed done: {db.query(Enterprise).count()} enterprises, {db.query(RiskCase).count()} cases")
    finally:
        db.close()


if __name__ == "__main__":
    main()
