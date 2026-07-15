import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.seed import seed_database
from app.models.base import SessionLocal


def main():
    db = SessionLocal()
    try:
        result = seed_database(db, n_enterprises=220, n_cases=520)
        print(f"Seeded: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
