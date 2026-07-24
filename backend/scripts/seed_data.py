import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.seed import init_real_data, seed_database
from app.models.base import Base, SessionLocal, engine


def main():
    """填充数据库。

    无参数：运行 seed_database()（Faker 假数据）
    --real：运行 init_real_data()（爬虫真实数据）
    """
    parser = argparse.ArgumentParser(description="舆情系统数据库初始化工具")
    parser.add_argument(
        "--real",
        action="store_true",
        help="使用爬虫采集真实数据填充（替代 Faker 假数据）",
    )
    args = parser.parse_args()

    # 确保所有表存在
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.real:
            print("正在使用爬虫采集真实数据...")
            result = init_real_data(db)
            print(f"真实数据初始化完成: {result}")
        else:
            print("正在使用 Faker 生成假数据...")
            result = seed_database(db, n_enterprises=220, n_cases=520)
            print(f"假数据填充完成: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
