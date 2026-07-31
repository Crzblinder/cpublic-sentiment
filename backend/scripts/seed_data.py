import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.init_real_data import DataInitializer
from app.models.base import Base, SessionLocal, engine


def main():
    """使用爬虫采集真实数据填充数据库。

    已彻底移除 Faker 假数据逻辑，仅保留真实数据初始化。
    """
    # 确保所有表存在
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("正在使用爬虫采集真实数据...")
        initializer = DataInitializer(db)
        result = initializer.run()
        print(f"真实数据初始化完成: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
