"""CLI entry point for the STEP58 category-correction migration (logic in
app/category_migration.py, shared with POST /admin/run-category-migration).

Safe by default: only PRINTS the plan unless --apply is passed.
Re-running with --apply is idempotent.

Usage:
    python scripts/category_migration.py            # dry run (default)
    python scripts/category_migration.py --apply     # writes for real
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.category_migration import run_category_migration  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main(apply: bool) -> None:
    db = SessionLocal()
    try:
        result = run_category_migration(db, apply=apply)
        for line in result.plan_lines:
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually write the changes (default: dry run)")
    main(apply=parser.parse_args().apply)
