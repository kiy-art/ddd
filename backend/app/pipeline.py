"""Shared analysis + AI-generation step, used by both the daily batch script
(scripts/update_prices.py) and the admin "run update" API endpoint so the
two never drift apart."""

import datetime
import json
import statistics
import time
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ai, analysis, content_rewriter, crud, email, forecast, image_urls, models, rakuten, yahoo
from app.config import get_settings
from app.rakuten import search_lowest_price

RAKUTEN_REQUEST_INTERVAL_SECONDS = 1.1  # stay under the API's ~1 req/sec free-tier limit
YAHOO_REQUEST_INTERVAL_SECONDS = 1.1  # same conservative pacing as Rakuten - no documented higher limit

# A freshly-fetched price outside this ratio of the product's known average
# is treated as a probable mismatch (wrong item matched, accessory/part
# picked up instead of the product, etc.) rather than a real price move, and
# is logged without being applied. See: PING G430 iron briefly showing a
# fake -98% ("¥1,100") price after a bad Rakuten search match.
PRICE_SANITY_MIN_RATIO = 0.5
PRICE_SANITY_MAX_RATIO = 2.0

# Item names that mark a Rakuten result as an accessory/part for the product
# rather than the product itself (a weight, a headcover, a bare shaft, ...).
# _is_plausible_price can't catch this on a product's very first price fetch
# (no reference price exists yet, so it accepts anything) — the actual gap
# that let an ELYTE MAX FAST driver's first-ever price briefly become a
# ¥2,180 sole-weight cap. Checked unconditionally, not just when there's no
# reference, since a plausible-looking price on an accessory is still wrong.
ACCESSORY_KEYWORDS = [
    "ヘッドカバー",
    "ヘッドカバ",
    "ウエイト",
    "ウェイト",
    "スリーブ",
    "シャフトのみ",
    "パーツ",
    "部品",
    "レンチ",
]


def _looks_like_accessory(item_name: str) -> bool:
    return any(keyword in item_name for keyword in ACCESSORY_KEYWORDS)


# A separate reject reason from ACCESSORY_KEYWORDS above: not "this is a
# part, not the product" but "this listing isn't a normal new-condition
# retail sale of the product at all" - a furusato nozei (ふるさと納税)
# donation-reward listing, or a damaged/defective clearance ("訳あり") item.
# Neither belongs in a price-comparison catalog even though the product
# name itself may be genuine. Deliberately NOT the same list as the title
# cleaner's promotional-phrase strip list (app/title_cleaner.py) - "送料
# 無料"/"ポイント"/"得" appear on nearly every real listing (including
# genuine golf clubs), so rejecting candidates on those would break normal
# discovery/price-matching; only these two mark the whole listing itself
# as not a real retail purchase.
NON_RETAIL_LISTING_KEYWORDS = [
    "ふるさと納税",
    "ふるさと",
    "訳あり",
]


def _looks_like_non_retail_listing(item_name: str) -> bool:
    return any(keyword in item_name for keyword in NON_RETAIL_LISTING_KEYWORDS)


def _is_plausible_price(product: models.Product, price: int) -> bool:
    reference = product.average_price or product.current_price
    if not reference:
        return True
    ratio = price / reference
    return PRICE_SANITY_MIN_RATIO <= ratio <= PRICE_SANITY_MAX_RATIO


def _regenerate_in_optimized_style(db: Session, product: models.Product, result: analysis.AnalysisResult) -> bool:
    """When a product's copy came from a content-optimizer decision (STEP43)
    and its price facts just changed, regenerate with that decision's goal
    and search queries instead of reverting to routine copy - otherwise the
    optimizer's improvement is erased the next day and its effect can
    never be measured. Only when ai.py would itself call Claude for this
    verdict, so this never adds a Claude call beyond the existing routine
    regeneration (docs/ai_company_guidelines.md absolute rule 1). Returns
    False (caller falls back to routine copy) if not eligible or it fails."""
    action = db.get(models.AiOptimizationAction, product.ai_copy_source_action_id)
    if action is None or action.status != "applied" or not action.content_after or not ai.would_use_claude(result):
        return False
    after = json.loads(action.content_after)
    try:
        rewritten = content_rewriter.rewrite_product_copy(
            product, action.decision_basis, goal=after.get("goal"), search_queries=after.get("queries") or []
        )
    except Exception as exc:  # noqa: BLE001 - fall back to routine copy rather than keep stale numbers
        crud.create_error_log(
            db, source="ai_generation", message=f"optimized-style regeneration failed, using routine copy: {exc}", product_id=product.id
        )
        return False
    product.ai_title = rewritten.title
    product.ai_summary = rewritten.summary
    product.ai_caution = rewritten.caution
    product.ai_generated_at = datetime.datetime.utcnow()
    return True


def sync_product_analysis(db: Session, product: models.Product) -> bool:
    """Recompute stats/buy_score from price history, refresh buy_reason, and
    regenerate AI wording only if the underlying facts changed (cost control).

    Returns True if AI content was (re)generated.
    """
    if product.current_price is None:
        return False

    history = crud.get_price_history(db, product.id)
    pairs = [(h.price, h.recorded_at) for h in history]
    result = analysis.analyze_prices(product.current_price, pairs, msrp=product.msrp)

    product.average_price = result.average_price
    product.lowest_price = result.lowest_price
    product.price_change_percent = result.price_change_percent
    product.buy_score = result.buy_score
    product.buy_signal_score = result.buy_signal_score
    product.history_span_days = result.history_span_days
    product.buy_reason = analysis.rule_based_reason(result)

    forecast_result = forecast.forecast_price(pairs, product.current_price, release_date=product.release_date)
    if forecast_result is None:
        product.forecast_confidence = None
        product.forecast_center_price = None
        product.forecast_low_price = None
        product.forecast_high_price = None
        product.forecast_target_date = None
        product.forecast_trend = None
        product.forecast_reason = None
    else:
        product.forecast_confidence = forecast_result.confidence
        product.forecast_center_price = forecast_result.center_price
        product.forecast_low_price = forecast_result.low_price
        product.forecast_high_price = forecast_result.high_price
        product.forecast_target_date = forecast_result.target_date
        product.forecast_trend = forecast_result.trend
        product.forecast_reason = "\n".join(forecast_result.reasons)

    new_hash = ai.content_hash(product.name, product.current_price, product.buy_score, product.average_price)
    if not ai.should_regenerate(product, new_hash):
        db.commit()
        return False

    if product.ai_copy_source_action_id is not None and _regenerate_in_optimized_style(db, product, result):
        product.ai_content_hash = new_hash
        db.commit()
        db.refresh(product)
        return True
    # Routine copy replaces whatever the optimizer wrote - clear the marker
    # so evaluate_past_actions knows that decision's copy is no longer live.
    product.ai_copy_source_action_id = None

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


def fetch_rakuten_prices(
    db: Session, on_progress: Callable[[int, int], None] | None = None
) -> tuple[int, int]:
    """Looks up each product's current price on Rakuten Ichiba by
    "brand + name" keyword search and records it as a new PriceHistory row.

    `on_progress(current, total)`, when given, is called once per product
    (after it's been processed, 1-indexed) - purely an optional progress
    report for the caller (see routers/admin.py + app/progress.py's live
    dashboard); omitting it changes nothing about this function's own
    behavior.

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
            if _looks_like_accessory(result.item_name) or _looks_like_non_retail_listing(result.item_name):
                crud.create_error_log(
                    db,
                    source="price_fetch",
                    level="warning",
                    message=(
                        f"{product.name}: 楽天の検索結果「{result.item_name}」はアクセサリ/パーツまたは"
                        "通常の新品販売ではない可能性が高いため自動反映をスキップしました"
                        f"（URL: {result.item_url}）"
                    ),
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
            # images). Only fill in what the site can't show (missing,
            # blank, invalid or a placeholder host - image_urls.needs_image)
            # - never overwrite a valid image or link an admin has curated.
            # The link points at the same Rakuten listing the photo/price
            # came from.
            changed = False
            new_image = image_urls.normalize_image_url(result.image_url)
            if new_image and image_urls.needs_image(product.image_url):
                product.image_url = new_image
                changed = True
            if result.item_url and not product.affiliate_url:
                product.affiliate_url = rakuten.to_affiliate_url(result.item_url) or result.item_url
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
        if on_progress is not None:
            on_progress(i + 1, len(products))
    return updated, skipped


def fetch_yahoo_prices(
    db: Session, on_progress: Callable[[int, int], None] | None = None
) -> tuple[int, int]:
    """Same shape as fetch_rakuten_prices, for a second independent price
    source (Yahoo!ショッピング). Writes to yahoo_price/yahoo_url/
    yahoo_updated_at only - never touches current_price/price_history/
    buy_score/forecast_*, which stay anchored to the single Rakuten-sourced
    series. When no match is found (or the match looks implausible/like an
    accessory), yahoo_price is cleared to None rather than left stale, so
    the store comparison table never shows an old price as current.

    Returns (updated_count, skipped_count).
    """
    products = list(db.execute(select(models.Product)).scalars().all())
    updated = 0
    skipped = 0
    for i, product in enumerate(products):
        if i > 0:
            time.sleep(YAHOO_REQUEST_INTERVAL_SECONDS)
        try:
            keyword = f"{product.brand} {product.name}".strip()
            result = yahoo.search_lowest_price(keyword)
            if (
                result is None
                or _looks_like_accessory(result.item_name)
                or _looks_like_non_retail_listing(result.item_name)
                or not _is_plausible_price(product, result.price)
            ):
                if product.yahoo_price is not None:
                    product.yahoo_price = None
                    product.yahoo_url = None
                    product.yahoo_updated_at = None
                    db.commit()
                skipped += 1
                continue
            product.yahoo_price = result.price
            product.yahoo_url = yahoo.to_affiliate_url(result.item_url) or result.item_url
            product.yahoo_updated_at = datetime.datetime.utcnow()
            # Yahoo's API likewise returns the listing's own photo. Used only
            # as a fallback when the product still has none the site can
            # show (e.g. Rakuten had no plausible match) - Rakuten's photo,
            # or an admin-curated one, always wins.
            yahoo_image = image_urls.normalize_image_url(result.image_url)
            if yahoo_image and image_urls.needs_image(product.image_url):
                product.image_url = yahoo_image
            db.commit()
            updated += 1
        except yahoo.YahooQuotaExceeded as exc:
            # Yahoo's daily call quota is exhausted for the whole batch, not
            # just this product - every remaining lookup this run would fail
            # identically, so stop now instead of logging the same error once
            # per remaining product (this is what produced ~25 near-identical
            # ErrorLog rows in a single run before this circuit breaker).
            db.rollback()
            remaining = len(products) - i
            crud.create_error_log(
                db,
                source="price_fetch",
                message=f"Yahoo: quota exhausted, stopping ({remaining} product(s) skipped this run): {exc}",
            )
            skipped += remaining
            if on_progress is not None:
                on_progress(len(products), len(products))
            break
        except Exception as exc:  # noqa: BLE001 - keep the batch alive
            db.rollback()
            crud.create_error_log(
                db, source="price_fetch", message=f"Yahoo: {product.name}: {exc}", product_id=product.id
            )
            skipped += 1
        if on_progress is not None:
            on_progress(i + 1, len(products))
    return updated, skipped


def send_price_alert_notifications(db: Session) -> tuple[int, int]:
    """Finds every untriggered price alert whose product has actually
    reached (or dropped below) the subscriber's own target price - the
    same real, already-stored condition the admin page already displays
    (see routers/admin.py's list_price_alerts) - and emails each one via
    Resend (app/email.py). A no-op (returns (0, 0) immediately) when
    RESEND_API_KEY isn't configured, matching how fetch_yahoo_prices treats
    an unconfigured optional integration.

    An alert is marked notified only after its email actually sends, so a
    Resend failure leaves it untouched and it's retried on the next run
    instead of being silently lost.

    Returns (sent_count, skipped_count).
    """
    settings = get_settings()
    if not settings.resend_api_key:
        return 0, 0

    sent = 0
    skipped = 0
    for alert in crud.list_price_alerts(db, only_untriggered=True):
        product = crud.get_product(db, alert.product_id)
        if product is None or product.current_price is None or product.current_price > alert.target_price:
            continue  # not triggered yet - not an error, just not due

        try:
            product_url = f"{settings.site_url}/products/{product.slug}"
            html = email.price_alert_email_html(
                product_name=product.name,
                product_url=product_url,
                current_price=product.current_price,
                target_price=alert.target_price,
            )
            email.send_email(
                to=alert.email,
                subject=f"【PAR.】{product.name}が目標価格以下になりました",
                html=html,
            )
            crud.mark_price_alert_notified(db, alert)
            sent += 1
        except Exception as exc:  # noqa: BLE001 - one bad send shouldn't block the rest
            crud.create_error_log(
                db,
                source="price_alert_email",
                message=f"{product.name} -> {alert.email}: {exc}",
                product_id=product.id,
            )
            skipped += 1
    return sent, skipped


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
