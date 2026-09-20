"""Shared analysis + AI-generation step, used by both the daily batch script
(scripts/update_prices.py) and the admin "run update" API endpoint so the
two never drift apart."""

import datetime
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ai, analysis, crud, models
from app.rakuten import search_lowest_price

RAKUTEN_REQUEST_INTERVAL_SECONDS = 1.1  # stay under the API's ~1 req/sec free-tier limit


def sync_product_analysis(db: Session, product: models.Product) -> bool:
    """Recompute stats/buy_score from price history, refresh buy_reason, and
    regenerate AI wording only if the underlying facts changed (cost control).

    Returns True if AI content was (re)generated.
    """
    if product.current_price is None:
        return False

    history = crud.get_price_history(db, product.id)
    pairs = [(h.price, h.recorded_at) for h in history]
    result = analysis.analyze_prices(product.current_price, pairs)

    product.average_price = result.average_price
    product.lowest_price = result.lowest_price
    product.price_change_percent = result.price_change_percent
    product.buy_score = result.buy_score
    product.buy_reason = analysis.rule_based_reason(result)

    new_hash = ai.content_hash(product.name, product.current_price, product.buy_score, product.average_price)
    if not ai.should_regenerate(product, new_hash):
        db.commit()
        return False

    content, error = ai.generate_ai_content_safe(product.name, product.brand, result)
    if error:
        crud.create_error_log(db, source="ai_generation", message=error, product_id=product.id)

    product.ai_title = content.title
    product.ai_summary = content.summary
    product.ai_caution = content.caution
    product.ai_generated_at = datetime.datetime.utcnow()
    product.ai_content_hash = new_hash
    db.commit()
    db.refresh(product)
    return True


def fetch_rakuten_prices(db: Session) -> tuple[int, int]:
    """Looks up each product's current price on Rakuten Ichiba by
    "brand + name" keyword search and records it as a new PriceHistory row.

    Returns (updated_count, skipped_count).
    """
    products = list(db.execute(select(models.Product)).scalars().all())
    updated = 0
    skipped = 0
    for i, product in enumerate(products):
        if i > 0:
            time.sleep(RAKUTEN_REQUEST_INTERVAL_SECONDS)
        try:
            keyword = f"{product.brand} {product.name}".strip()
            result = search_lowest_price(keyword)
            if result is None:
                crud.create_error_log(
                    db,
                    source="price_fetch",
                    level="info",
                    message=f"{product.name}: 楽天市場で該当商品が見つかりませんでした（キーワード: {keyword}）",
                    product_id=product.id,
                )
                skipped += 1
                continue
            crud.add_price(db, product, result.price)
            updated += 1
        except Exception as exc:  # noqa: BLE001 - keep the batch alive
            db.rollback()
            crud.create_error_log(
                db, source="price_fetch", message=f"{product.name}: {exc}", product_id=product.id
            )
            skipped += 1
    return updated, skipped
