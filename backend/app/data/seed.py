"""使用爬虫采集真实数据填充数据库，替代 Faker 假数据。

调用 DataInitializer 执行：爬虫采集 → 清洗管线
→ 入库（RiskCase / Enterprise / SentimentEvent）。
"""

from typing import Any

from sqlalchemy.orm import Session


def init_real_data(db: Session) -> dict[str, Any]:
    """使用爬虫采集真实数据填充数据库，替代 Faker 假数据。

    调用 DataInitializer 执行：爬虫采集 → 清洗管线
    → 入库（RiskCase / Enterprise / SentimentEvent）。
    """
    from app.data.init_real_data import DataInitializer

    initializer = DataInitializer(db)
    return initializer.run()
