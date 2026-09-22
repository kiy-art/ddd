"""Backfills msrp/release_date onto existing products from a hand-researched
CSV (brand,model_number,msrp,release_date - either value may be blank).

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
