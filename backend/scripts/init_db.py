import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.base import Base, engine


def main():
    print("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    print("Database schema ready.")


if __name__ == "__main__":
    main()
