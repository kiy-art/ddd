"""CLI entry point for the STEP15 title-cleanup + duplicate-merge
migration. The actual logic lives in app/title_migration.py (shared with
the admin-panel equivalent, POST /admin/run-migration-clean-titles - see
that module's own docstring for why both exist).

Safe by default: this only PRINTS a plan and makes no database changes
unless --apply is passed. Re-running with --apply is idempotent - a
product already renamed to its clean form, or already merged, has
nothing left to do next time.

Recommended: back up the database before running with --apply. For local
SQLite, copy the .db file. For the production Postgres database on
Render, take a backup/snapshot through Render's dashboard first.

Usage:
    python scripts/migrate_clean_titles.py            # dry run (default)
    python scripts/migrate_clean_titles.py --apply     # writes for real
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.title_migration import run_title_cleanup_migration  # noqa: E402


def main(apply: bool) -> None:
    db = SessionLocal()
    try:
        result = run_title_cleanup_migration(db, apply=apply)
        for line in result.plan_lines:
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="実際にDBへ変更を書き込む（省略時はdry-run）")
    args = parser.parse_args()
    main(apply=args.apply)
