"""Shared analysis + AI-generation step, used by both the daily batch script
(scripts/update_prices.py) and the admin "run update" API endpoint so the
two never drift apart."""

import datetime
import statistics
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ai, analysis, crud, models
from app.rakuten import search_lowest_price

RAKUTEN_REQUEST_INTERVAL_SECONDS = 1.1  # stay under the API's ~1 req/sec free-tier limit

# A freshly-fetched price outside this ratio of the product's known average
# is treated as a probable mismatch (wrong item matched, accessory/part
# picked up instead of the product, etc.) rather than a real price move, and
# is logged without being applied. See: PING G430 iron briefly showing a
# fake -98% ("¥1,100") price after a bad Rakuten search match.
PRICE_SANITY_MIN_RATIO = 0.5
PRICE_SANITY_MAX_RATIO = 2.0


def _is_plausible_price(product: models.Product, price: int) -> bool:
    reference = product.average_price or product.current_price
    if not reference:
        return True
    ratio = price / reference
    return PRICE_SANITY_MIN_RATIO <= ratio <= PRICE_SANITY_MAX_RATIO


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
            if not _is_plausible_price(product, result.price):
                reference = product.average_price or product.current_price
                crud.create_error_log(
                    db,
                    source="price_fetch",
                    level="warning",
                    message=(
                        f"{product.name}: 楽天の検索結果 ¥{result.price:,} が既存価格（参考値 ¥{reference:,}）"
                        "と大きく乖離しているため、誤検出の可能性が高いと判断し自動反映をスキップしました"
                        f"（マッチした商品名: {result.item_name} / URL: {result.item_url}）"
                    ),
                    product_id=product.id,
                )
                skipped += 1
                continue
            crud.add_price(db, product, result.price)
            # Rakuten's API returns the item's own listing photo, provided
            # for exactly this kind of use (unlike hotlinking e.g. Amazon
            # images). Only fill in blanks — never overwrite an image or
            # link an admin has manually curated. The link points at the
            # same Rakuten listing the photo/price came from.
            changed = False
            if result.image_url and not product.image_url:
                product.image_url = result.image_url
                changed = True
            if result.item_url and not product.affiliate_url:
                product.affiliate_url = result.item_url
                changed = True
            if changed:
                db.commit()
            updated += 1
        except Exception as exc:  # noqa: BLE001 - keep the batch alive
            db.rollback()
            crud.create_error_log(
                db, source="price_fetch", message=f"{product.name}: {exc}", product_id=product.id
            )
            skipped += 1
    return updated, skipped


def find_price_anomalies(db: Session) -> list[dict]:
    """Scans every product's existing price history for rows that look like
    a bad Rakuten match recorded before the sanity-check guard existed (a
    price wildly off from the product's other recorded prices), so they can
    be reviewed and cleaned up. Each product needs >=2 history rows to have
    a reference to compare against."""
    products = list(db.execute(select(models.Product)).scalars().all())
    anomalies: list[dict] = []
    for product in products:
        history = crud.get_price_history(db, product.id)
        if len(history) < 2:
            continue
        for row in history:
            others = [h.price for h in history if h.id != row.id]
            reference = statistics.median(others)
            if reference <= 0:
                continue
            ratio = row.price / reference
            if PRICE_SANITY_MIN_RATIO <= ratio <= PRICE_SANITY_MAX_RATIO:
                continue
            anomalies.append(
                {
                    "price_history_id": row.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_slug": product.slug,
                    "price": row.price,
                    "recorded_at": row.recorded_at,
                    "reference_price": round(reference),
                    "ratio": round(ratio, 3),
                }
            )
    return anomalies


def fix_price_anomalies(db: Session) -> list[dict]:
    """Deletes every flagged anomaly row and recomputes the affected
    products' current/average/lowest price and buy_score from what remains."""
    anomalies = find_price_anomalies(db)
    affected_product_ids: set[int] = set()
    for anomaly in anomalies:
        crud.delete_price(db, anomaly["price_history_id"])
        affected_product_ids.add(anomaly["product_id"])
    for product_id in affected_product_ids:
        product = crud.get_product(db, product_id)
        if product is None:
            continue
        crud.recompute_current_price(db, product)
        if product.current_price is not None:
            sync_product_analysis(db, product)
    return anomalies
