"""CLI entry point for applying the hand-researched maker facts
(backend/data/product_facts.csv) - logic in app/product_facts.py, shared
with POST /admin/run-product-facts (the way to run it on production,
which has no shell). Never overwrites a value already set.

Safe by default: only PRINTS the plan unless --apply is passed.

Usage:
    python scripts/set_product_facts.py            # dry run (default)
    python scripts/set_product_facts.py --apply     # writes for real
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.product_facts import run_product_facts  # noqa: E402


def main(apply: bool) -> None:
    db = SessionLocal()
    try:
        for line in run_product_facts(db, apply=apply).plan_lines:
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually write the changes (default: dry run)")
    main(apply=parser.parse_args().apply)
