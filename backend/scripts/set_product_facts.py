"""Backfills msrp/release_date/skill_level/performance_type/is_current_generation
onto existing products from a hand-researched CSV (brand,model_number,msrp,
release_date,skill_level,performance_type,is_current_generation - any value
may be blank).

These are manually-curated facts (see the comment on Product.msrp), so this
never overwrites a value that's already set - not by this script on a
previous run, and not by an admin who edited it by hand. Safe to re-run.

Usage: python scripts/set_product_facts.py ../data/product_facts.csv
"""

import csv
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_product_facts.py <path-to-csv>", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    matched = 0
    skipped_no_match = 0
    skipped_already_set = 0

    db = SessionLocal()
    try:
        with csv_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                brand = row["brand"].strip()
                model_number = row["model_number"].strip()
                msrp = int(row["msrp"]) if row.get("msrp", "").strip() else None
                release_date = (
                    datetime.date.fromisoformat(row["release_date"].strip())
                    if row.get("release_date", "").strip()
                    else None
                )
                skill_level = row.get("skill_level", "").strip() or None
                performance_type = row.get("performance_type", "").strip() or None
                is_current_generation_raw = row.get("is_current_generation", "").strip().lower()
                is_current_generation = (
                    is_current_generation_raw in ("true", "1", "yes") if is_current_generation_raw else None
                )

                products = list(
                    db.execute(
                        select(models.Product).where(
                            models.Product.brand == brand, models.Product.model_number == model_number
                        )
                    ).scalars()
                )
                if not products:
                    print(f"no match: {brand} / {model_number}")
                    skipped_no_match += 1
                    continue

                for product in products:
                    changed = False
                    if msrp is not None and product.msrp is None:
                        product.msrp = msrp
                        changed = True
                    if release_date is not None and product.release_date is None:
                        product.release_date = release_date
                        changed = True
                    if skill_level is not None and product.skill_level is None:
                        product.skill_level = skill_level
                        changed = True
                    if performance_type is not None and product.performance_type is None:
                        product.performance_type = performance_type
                        changed = True
                    if is_current_generation is not None and product.is_current_generation is None:
                        product.is_current_generation = is_current_generation
                        changed = True
                    if changed:
                        matched += 1
                    else:
                        skipped_already_set += 1

        db.commit()
    finally:
        db.close()

    print(f"Updated: {matched}, no match: {skipped_no_match}, already set: {skipped_already_set}")


if __name__ == "__main__":
    main()
