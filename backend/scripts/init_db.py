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

from sqlalchemy import Engine, inspect, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from sqlalchemy import select  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app import consumables_merchandiser, crud, models, rakuten  # noqa: E402,F401  (import registers the models on Base)

# Columns added after the initial schema. Keep this list append-only.
ADDED_COLUMNS = [
    ("products", "buy_signal_score", "INTEGER"),
    ("products", "history_span_days", "INTEGER"),
    ("products", "pending_review", "BOOLEAN"),
    ("products", "forecast_confidence", "VARCHAR(10)"),
    ("products", "forecast_center_price", "INTEGER"),
    ("products", "forecast_low_price", "INTEGER"),
    ("products", "forecast_high_price", "INTEGER"),
    ("products", "forecast_target_date", "TIMESTAMP"),
    ("products", "forecast_trend", "VARCHAR(10)"),
    ("products", "forecast_reason", "TEXT"),
    ("products", "msrp", "INTEGER"),
    ("products", "release_date", "DATE"),
    ("products", "popularity_rank", "INTEGER"),
    ("products", "popularity_updated_at", "TIMESTAMP"),
    ("products", "skill_level", "VARCHAR(20)"),
    ("products", "performance_type", "VARCHAR(20)"),
    ("products", "is_current_generation", "BOOLEAN"),
    ("products", "yahoo_price", "INTEGER"),
    ("products", "yahoo_url", "VARCHAR(1024)"),
    ("products", "yahoo_updated_at", "TIMESTAMP"),
    ("products", "ai_copy_source_action_id", "INTEGER"),
    ("ai_optimization_actions", "revert_reason", "VARCHAR(30)"),
]


def migrate(target_engine: Engine) -> None:
    """Creates any missing tables/columns and backfills any that a bare
    ADD COLUMN would otherwise leave NULL on pre-existing rows. Idempotent -
    safe to call on every deploy."""
    Base.metadata.create_all(bind=target_engine)

    inspector = inspect(target_engine)
    with target_engine.begin() as conn:
        for table, column, coltype in ADDED_COLUMNS:
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))

        # `history_span_days` is non-nullable in the API schema (ProductOut),
        # but a bare ADD COLUMN leaves it NULL on every row that already
        # existed - which made every /api/products response fail Pydantic
        # validation with a 500 ("商品情報の取得に失敗しました") until this
        # backfill ran.
        conn.execute(text("UPDATE products SET history_span_days = 0 WHERE history_span_days IS NULL"))

        # Same NULL-on-preexisting-rows problem as above: pending_review is
        # non-nullable (bool) in ProductOut. Every row that existed before
        # this column was added must default to already-published (False),
        # not pending — only the auto-discovery pipeline ever sets True.
        conn.execute(text("UPDATE products SET pending_review = FALSE WHERE pending_review IS NULL"))


# One-off correction for a specific known-bad production row: "ELYTE MAX
# FAST ドライバー" had no price history yet (freshly imported from CSV, no
# initial_price recorded) when the daily Rakuten fetch ran, so
# _is_plausible_price had no reference price to check against and accepted
# whatever it matched — in this case a ¥2,180 sole-weight-port accessory
# listing, complete with its photo. Re-running fetch_rakuten_prices alone
# won't fix it (the bad price is now its own reference), so this restores
# the real, manually-researched price from data/real_products_batch1.csv
# and clears the accessory photo/link so a correct one can be filled in on
# the next fetch. Idempotent: no-ops once the price is back above the
# no-real-driver-costs-this-little threshold below.
KNOWN_BAD_PRODUCT_FIXES = [
    {
        "name": "ELYTE MAX FAST ドライバー",
        "brand": "Callaway",
        "model_number": "ELYTE MAX FAST",
        "bad_price_ceiling": 10000,
        "correct_price": 107800,
    },
]


def fix_known_bad_products(db: Session) -> None:
    for fix in KNOWN_BAD_PRODUCT_FIXES:
        product = crud.find_product_by_identity(db, fix["name"], fix["brand"], fix["model_number"])
        if product is None:
            continue
        if product.current_price is None or product.current_price >= fix["bad_price_ceiling"]:
            continue
        for row in crud.get_price_history(db, product.id):
            crud.delete_price(db, row.id)
        product.image_url = None
        product.affiliate_url = None
        db.commit()
        crud.add_price(db, product, fix["correct_price"])


# Every affiliate_url filled in before RAKUTEN_AFFILIATE_ID was configured
# is a plain (non-tracked) Rakuten item link, so those products' purchases
# never earned a commission. Once the ID is set, rewrite every plain
# Rakuten link into a tracked one - a no-op (and safe to keep re-running)
# once nothing plain is left, and it does nothing at all until the ID is
# configured, matching rakuten.to_affiliate_url's own behavior.
def wrap_existing_affiliate_links(db: Session) -> int:
    from app.config import get_settings

    if not get_settings().rakuten_affiliate_id:
        return 0

    rewrapped = 0
    products = list(db.execute(select(models.Product)).scalars().all())
    for product in products:
        url = product.affiliate_url
        if not url or not url.startswith("https://item.rakuten.co.jp/"):
            continue
        product.affiliate_url = rakuten.to_affiliate_url(url)
        rewrapped += 1
    if rewrapped:
        db.commit()
    return rewrapped


def main():
    migrate(engine)
    with SessionLocal() as db:
        fix_known_bad_products(db)
        wrap_existing_affiliate_links(db)
        # STEP52: insert any new consumables-corner catalog items (never
        # overwrites existing rows - prices, history, admin-set msrp stay).
        consumables_merchandiser.seed_catalog(db)
    print("Tables created.")


if __name__ == "__main__":
    main()
