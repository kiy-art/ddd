"""Create all tables. MVP uses this instead of a migration tool (see README).

Usage: python scripts/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (import registers the models on Base)


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()
