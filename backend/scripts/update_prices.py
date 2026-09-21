"""Daily batch job.

Pipeline (spec section 9):
  1. load product list
  2. fetch prices — Rakuten Ichiba Item Search API when RAKUTEN_APP_ID is
     configured, otherwise CSV import (--csv PATH), otherwise skipped
  3. save PriceHistory
  4. update price stats
  5. determine buy_score
  6. generate AI wording (only when facts changed - cost control)
  7. (site reflects DB state directly via the public API)

Any per-product failure is logged to ErrorLog and skipped, the batch keeps going.

Usage:
  python scripts/update_prices.py --csv ../data/sample_products.csv
  python scripts/update_prices.py            # uses Rakuten if configured, else re-runs analysis only
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app import crud, models, pipeline  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.csv_import import import_csv  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Path to a price CSV to import before analysis", default=None)
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        if args.csv:
            csv_path = Path(args.csv)
            if not csv_path.exists():
                print(f"CSV not found: {csv_path}", file=sys.stderr)
                sys.exit(1)
            result = import_csv(db, csv_path.read_bytes())
            print(
                f"CSV import: created={result.created_products} "
                f"updated={result.updated_products} prices={result.prices_recorded} "
                f"errors={len(result.errors)}"
            )
            for err in result.errors:
                print(f"  - {err}")
        elif settings.rakuten_app_id and settings.rakuten_access_key:
            updated, skipped = pipeline.fetch_rakuten_prices(db)
            print(f"Rakuten fetch: updated={updated} skipped={skipped}")
        else:
            print("No --csv given and RAKUTEN_APP_ID not set; re-running analysis only.")

        products = list(db.execute(select(models.Product)).scalars().all())
        checked = 0
        regenerated = 0
        skipped_analysis = 0
        for product in products:
            try:
                checked += 1
                if pipeline.sync_product_analysis(db, product):
                    regenerated += 1
            except Exception as exc:  # noqa: BLE001 - keep the batch alive
                skipped_analysis += 1
                db.rollback()
                crud.create_error_log(
                    db, source="price_fetch", message=f"{product.name}: {exc}", product_id=product.id
                )

        print(f"Analysis: checked={checked} ai_regenerated={regenerated} skipped_on_error={skipped_analysis}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
