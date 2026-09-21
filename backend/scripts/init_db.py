"""Create all tables. MVP uses this instead of a migration tool (see README).

`create_all` only creates missing *tables*, never adds columns to a table
that already exists — which matters once there's real data in Render's
Postgres. So new columns are added here too: we inspect what already
exists and only ALTER TABLE ADD COLUMN for what's missing (safe to re-run
on every deploy, no-op once a column exists). This has to be done by
inspecting first rather than `ADD COLUMN IF NOT EXISTS`, since SQLite's
ALTER TABLE doesn't support that clause (Postgres does, but this needs to
work for local SQLite dev too). Once the schema is more stable this should
become a real Alembic migration instead (see README).

Usage: python scripts/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (import registers the models on Base)

# Columns added after the initial schema. Keep this list append-only.
ADDED_COLUMNS = [
    ("products", "buy_signal_score", "INTEGER"),
    ("products", "history_span_days", "INTEGER"),
]


def main():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, coltype in ADDED_COLUMNS:
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))

    print("Tables created.")


if __name__ == "__main__":
    main()
