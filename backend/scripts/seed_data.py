import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.seed import seed_database
from app.models.base import Base, SessionLocal, engine


def main():
    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_database(db, n_enterprises=220, n_cases=520)
        print(f"Seeded: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
