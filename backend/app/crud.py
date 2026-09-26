import datetime
import re

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import analysis, models, schemas


def slugify(*parts: str) -> str:
    text = "-".join(p for p in parts if p).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "product"


def unique_slug(db: Session, base: str, exclude_id: int | None = None) -> str:
    slug = base
    n = 2
    while True:
        query = select(models.Product).where(models.Product.slug == slug)
        if exclude_id is not None:
            query = query.where(models.Product.id != exclude_id)
        existing = db.execute(query).scalar_one_or_none()
        if existing is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


# --- Product ---------------------------------------------------------------


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.get(models.Product, product_id)


def get_product_by_slug(db: Session, slug: str, exclude_pending: bool = False) -> models.Product | None:
    query = select(models.Product).where(models.Product.slug == slug)
    if exclude_pending:
        query = query.where(models.Product.pending_review.is_(False))
    return db.execute(query).scalar_one_or_none()


def find_product_by_identity(
    db: Session, name: str, brand: str, model_number: str | None
) -> models.Product | None:
    query = select(models.Product).where(models.Product.name == name, models.Product.brand == brand)
    if model_number:
        query = query.where(models.Product.model_number == model_number)
    return db.execute(query).scalars().first()


def list_products(
    db: Session,
    category: str | None = None,
    brand: str | None = None,
    buy_score: str | None = None,
    published_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Product]:
    query = select(models.Product)
    if category:
        query = query.where(models.Product.category == category)
    if brand:
        query = query.where(models.Product.brand == brand)
    if buy_score:
        query = query.where(models.Product.buy_score == buy_score)
    if published_only:
        query = query.where(models.Product.buy_score != "insufficient_data")
        query = query.where(models.Product.pending_review.is_(False))
    query = query.order_by(models.Product.price_change_percent.asc().nulls_last())
    query = query.offset(offset).limit(limit)
    return list(db.execute(query).scalars().all())


# Same bar the frontend uses (THIN_DATA_DAYS in ProductCard.tsx/product
# page) before treating a product's price_change_percent as a real trend
# rather than noise from a handful of data points - reused here so a
# brand's aggregate stats don't overstate what thin per-product data
# actually supports.
RELIABLE_TREND_MIN_HISTORY_DAYS = 7


def get_brand_price_stats(db: Session, brand: str) -> schemas.BrandPriceStats:
    """Aggregates real price movement across a brand's own tracked products
    - never an editorial claim about "the brand" from outside data. Every
    number here is computed straight from each product's own PriceHistory/
    msrp, the same fields already shown on its own page."""
    products = list_products(db, brand=brand, published_only=True, limit=1000)
    reliable = [
        p
        for p in products
        if p.buy_score != "insufficient_data" and p.history_span_days >= RELIABLE_TREND_MIN_HISTORY_DAYS
    ]

    declining = [p for p in reliable if p.price_change_percent is not None and p.price_change_percent < 0]
    rising = [p for p in reliable if p.price_change_percent is not None and p.price_change_percent > 0]
    flat = [p for p in reliable if p.price_change_percent == 0]

    changes = [p.price_change_percent for p in reliable if p.price_change_percent is not None]
    average_change_percent = round(sum(changes) / len(changes), 1) if changes else None

    msrp_discounts = [
        ((p.current_price - p.msrp) / p.msrp) * 100
        for p in products
        if p.msrp and p.current_price is not None
    ]
    average_msrp_discount_percent = (
        round(sum(msrp_discounts) / len(msrp_discounts), 1) if msrp_discounts else None
    )

    biggest_decline = None
    if declining:
        worst = min(declining, key=lambda p: p.price_change_percent)
        biggest_decline = schemas.BrandPriceMover(
            product_slug=worst.slug, product_name=worst.name, change_percent=worst.price_change_percent
        )

    return schemas.BrandPriceStats(
        brand=brand,
        tracked_count=len(products),
        reliable_count=len(reliable),
        declining_count=len(declining),
        rising_count=len(rising),
        flat_count=len(flat),
        average_change_percent=average_change_percent,
        average_msrp_discount_percent=average_msrp_discount_percent,
        biggest_decline=biggest_decline,
    )


def list_brands(db: Session, published_only: bool = True) -> list[tuple[str, int]]:
    """Distinct brands with a product count, sorted by count desc then name."""
    query = select(models.Product.brand, func.count(models.Product.id)).group_by(models.Product.brand)
    if published_only:
        query = query.where(models.Product.buy_score != "insufficient_data")
        query = query.where(models.Product.pending_review.is_(False))
    query = query.order_by(func.count(models.Product.id).desc(), models.Product.brand.asc())
    return [(row[0], row[1]) for row in db.execute(query).all()]


def create_product(db: Session, data: schemas.ProductCreate, pending_review: bool = False) -> models.Product:
    slug_parts = [data.brand, data.name]
    if data.model_number and data.model_number.lower() not in data.name.lower():
        slug_parts.append(data.model_number)
    base_slug = data.slug or slugify(*slug_parts)
    slug = unique_slug(db, base_slug)
    product = models.Product(
        slug=slug,
        name=data.name,
        brand=data.brand,
        category=data.category,
        model_number=data.model_number,
        image_url=data.image_url,
        product_url=data.product_url,
        affiliate_url=data.affiliate_url,
        msrp=data.msrp,
        release_date=data.release_date,
        skill_level=data.skill_level,
        performance_type=data.performance_type,
        is_current_generation=data.is_current_generation,
        buy_score="insufficient_data",
        pending_review=pending_review,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    if data.initial_price is not None:
        add_price(db, product, data.initial_price)
    return product


def approve_product(db: Session, product: models.Product) -> models.Product:
    product.pending_review = False
    db.commit()
    db.refresh(product)
    return product


def list_pending_products(db: Session) -> list[models.Product]:
    query = select(models.Product).where(models.Product.pending_review.is_(True)).order_by(
        models.Product.created_at.desc()
    )
    return list(db.execute(query).scalars().all())


def update_product(db: Session, product: models.Product, data: schemas.ProductUpdate) -> models.Product:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: models.Product) -> None:
    db.delete(product)
    db.commit()


# --- Price history -----------------------------------------------------------


def add_price(
    db: Session,
    product: models.Product,
    price: int,
    recorded_at: datetime.datetime | None = None,
) -> models.PriceHistory:
    recorded_at = recorded_at or datetime.datetime.utcnow()
    history_row = models.PriceHistory(product_id=product.id, price=price, recorded_at=recorded_at)
    db.add(history_row)
    db.commit()

    history = db.execute(
        select(models.PriceHistory).where(models.PriceHistory.product_id == product.id)
    ).scalars().all()
    pairs = [(h.price, h.recorded_at) for h in history]

    result = analysis.analyze_prices(price, pairs, now=recorded_at, msrp=product.msrp)

    product.previous_price = product.current_price
    product.current_price = price
    product.average_price = result.average_price
    product.lowest_price = result.lowest_price
    product.price_change_percent = result.price_change_percent
    product.buy_score = result.buy_score
    product.buy_signal_score = result.buy_signal_score
    product.history_span_days = result.history_span_days
    db.commit()
    db.refresh(product)
    return history_row


def get_price_history(db: Session, product_id: int) -> list[models.PriceHistory]:
    query = (
        select(models.PriceHistory)
        .where(models.PriceHistory.product_id == product_id)
        .order_by(models.PriceHistory.recorded_at.asc())
    )
    return list(db.execute(query).scalars().all())


def delete_price(db: Session, price_history_id: int) -> int | None:
    """Deletes a single (erroneous) price-history row. Returns the owning
    product's id, or None if the row didn't exist."""
    row = db.get(models.PriceHistory, price_history_id)
    if row is None:
        return None
    product_id = row.product_id
    db.delete(row)
    db.commit()
    return product_id


def recompute_current_price(db: Session, product: models.Product) -> None:
    """Resets current/previous price from remaining history after a row is
    deleted, since add_price() is the only other place these fields are set."""
    history = get_price_history(db, product.id)
    if not history:
        product.current_price = None
        product.previous_price = None
        product.average_price = None
        product.lowest_price = None
        product.price_change_percent = None
        product.buy_score = "insufficient_data"
        product.buy_signal_score = None
        product.history_span_days = 0
    else:
        product.current_price = history[-1].price
        product.previous_price = history[-2].price if len(history) >= 2 else None
    db.commit()
    db.refresh(product)


# --- Price alerts ----------------------------------------------------------------


def create_price_alert(db: Session, product: models.Product, data: schemas.PriceAlertCreate) -> models.PriceAlert:
    alert = models.PriceAlert(product_id=product.id, email=data.email, target_price=data.target_price)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_price_alerts(db: Session, only_untriggered: bool = False) -> list[models.PriceAlert]:
    query = select(models.PriceAlert).order_by(models.PriceAlert.created_at.desc())
    if only_untriggered:
        query = query.where(models.PriceAlert.notified_at.is_(None))
    return list(db.execute(query).scalars().all())


def mark_price_alert_notified(db: Session, alert: models.PriceAlert) -> None:
    alert.notified_at = datetime.datetime.utcnow()
    db.commit()


# --- Contact messages -------------------------------------------------------


def create_contact_message(db: Session, data: schemas.ContactMessageCreate) -> models.ContactMessage:
    message = models.ContactMessage(name=data.name, email=data.email, message=data.message)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_contact_messages(db: Session) -> list[models.ContactMessage]:
    query = select(models.ContactMessage).order_by(models.ContactMessage.created_at.desc())
    return list(db.execute(query).scalars().all())


def mark_contact_message_read(db: Session, message: models.ContactMessage) -> models.ContactMessage:
    message.read_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message


# --- Affiliate clicks -------------------------------------------------------


def create_affiliate_click(db: Session, data: schemas.AffiliateClickCreate) -> models.AffiliateClick:
    # A public, unauthenticated endpoint feeds this from the browser (see
    # routers/products.py's track_affiliate_click) - a stale/tampered
    # product_id must never turn a real click into a failed request, so an
    # id that doesn't exist is stored as None rather than left to violate
    # the FK constraint (Postgres enforces it; a bare INSERT would 500).
    product_id = data.product_id
    if product_id is not None and db.get(models.Product, product_id) is None:
        product_id = None
    click = models.AffiliateClick(product_id=product_id, category=data.category, shop=data.shop, placement=data.placement)
    db.add(click)
    db.commit()
    db.refresh(click)
    return click


# Caps how many of each list the summary endpoint returns - this is a
# dashboard snapshot, not a full export, so an ever-growing clicks table
# never makes a single admin page load slower.
_AFFILIATE_CLICK_TOP_PRODUCTS_LIMIT = 10
_AFFILIATE_CLICK_RECENT_LIMIT = 30


def get_affiliate_click_summary(db: Session) -> schemas.AffiliateClickSummary:
    """Real, first-party click counts - never estimated or backfilled from
    GA4 (which may not even be configured, see analytics_ga4.py). Every
    number here is a literal COUNT(*) over rows this site itself recorded
    at the moment of a real outbound click (see create_affiliate_click)."""
    total = db.execute(select(func.count()).select_from(models.AffiliateClick)).scalar_one()

    by_shop_rows = db.execute(
        select(models.AffiliateClick.shop, func.count())
        .group_by(models.AffiliateClick.shop)
        .order_by(func.count().desc())
    ).all()
    by_shop = [schemas.ShopClickCount(shop=shop, count=count) for shop, count in by_shop_rows]

    top_rows = db.execute(
        select(models.AffiliateClick.product_id, func.count().label("clicks"))
        .where(models.AffiliateClick.product_id.is_not(None))
        .group_by(models.AffiliateClick.product_id)
        .order_by(func.count().desc())
        .limit(_AFFILIATE_CLICK_TOP_PRODUCTS_LIMIT)
    ).all()
    top_products: list[schemas.ProductClickCount] = []
    for product_id, clicks in top_rows:
        product = db.get(models.Product, product_id)
        if product is None:
            continue  # the product was deleted since these clicks were recorded
        top_products.append(
            schemas.ProductClickCount(
                product_id=product_id, product_name=product.name, product_slug=product.slug, clicks=clicks
            )
        )

    recent_rows = db.execute(
        select(models.AffiliateClick)
        .order_by(models.AffiliateClick.created_at.desc())
        .limit(_AFFILIATE_CLICK_RECENT_LIMIT)
    ).scalars().all()
    recent: list[schemas.AffiliateClickRecentOut] = []
    for click in recent_rows:
        product = db.get(models.Product, click.product_id) if click.product_id is not None else None
        recent.append(
            schemas.AffiliateClickRecentOut(
                id=click.id,
                product_id=click.product_id,
                category=click.category,
                shop=click.shop,
                placement=click.placement,
                created_at=click.created_at,
                product_name=product.name if product else None,
                product_slug=product.slug if product else None,
            )
        )

    return schemas.AffiliateClickSummary(total=total, by_shop=by_shop, top_products=top_products, recent=recent)


# --- Error logs ----------------------------------------------------------------


def create_error_log(
    db: Session,
    source: str,
    message: str,
    level: str = "error",
    product_id: int | None = None,
) -> models.ErrorLog:
    log = models.ErrorLog(source=source, message=message, level=level, product_id=product_id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_error_logs(db: Session, limit: int = 100, offset: int = 0) -> list[models.ErrorLog]:
    query = (
        select(models.ErrorLog)
        .order_by(models.ErrorLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(query).scalars().all())


def count_error_logs_by_level(db: Session) -> dict[str, int]:
    """Real counts, grouped by level, over the *entire* table - not just
    whatever page /admin/logs happens to be showing. Used by the AI War
    Room's CPO/Compliance personas so "N件のエラー" always reflects the
    actual table, not an artifact of a 100-row page size."""
    rows = db.execute(select(models.ErrorLog.level, func.count()).group_by(models.ErrorLog.level)).all()
    return {level: count for level, count in rows}


def cleanup_error_logs(db: Session, retention_days: dict[str, int]) -> dict[str, int]:
    """Deletes ErrorLog rows older than a per-level retention window
    (e.g. {"info": 14, "warning": 14, "error": 30}) - a level not present
    in the dict is left untouched. Returns the number of rows deleted per
    level that was actually acted on.

    Two callers use this with different windows (see routers/admin.py):
    the daily batch job applies a long, quiet retention so the table
    never grows unbounded; the admin-triggered "AI自動修復" action applies
    a short one to immediately clear routine/aging noise on demand."""
    deleted: dict[str, int] = {}
    now = datetime.datetime.utcnow()
    for level, days in retention_days.items():
        cutoff = now - datetime.timedelta(days=days)
        result = db.execute(
            delete(models.ErrorLog).where(models.ErrorLog.level == level, models.ErrorLog.created_at < cutoff)
        )
        deleted[level] = result.rowcount or 0
    db.commit()
    return deleted


# --- STEP42: content optimization loop (guides, optimization actions) ------


def list_guide_articles(db: Session) -> list[models.GuideArticle]:
    query = select(models.GuideArticle).order_by(models.GuideArticle.published_at.desc())
    return list(db.execute(query).scalars().all())


def get_guide_article_by_slug(db: Session, slug: str) -> models.GuideArticle | None:
    return db.execute(select(models.GuideArticle).where(models.GuideArticle.slug == slug)).scalar_one_or_none()


def list_optimization_actions(db: Session, limit: int = 50, offset: int = 0) -> list[models.AiOptimizationAction]:
    query = (
        select(models.AiOptimizationAction)
        .order_by(models.AiOptimizationAction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(query).scalars().all())


class OptimizationActionNotRevertible(Exception):
    pass


def revert_optimization_action(db: Session, action_id: int) -> models.AiOptimizationAction:
    """Restores the product's ai_title/ai_summary/ai_caution from the
    action's own content_before snapshot - the concrete "if it was wrong,
    undo it" remedy the president asked for, alongside the effect-
    evaluation knowledge trail (see app/content_optimizer.py). Only
    rewrite_product actions can be reverted this way (a new_guide action
    is undone by deleting/unpublishing the GuideArticle instead, and
    reorder_homepage is self-correcting the next time the daily loop runs)."""
    import json as _json

    action = db.get(models.AiOptimizationAction, action_id)
    if action is None:
        raise ValueError("Optimization action not found")
    if action.action_type != "rewrite_product" or action.status != "applied":
        raise OptimizationActionNotRevertible("Only an applied rewrite_product action can be reverted")
    if action.reverted_at is not None:
        raise OptimizationActionNotRevertible("This action was already reverted")
    if not action.content_before:
        raise OptimizationActionNotRevertible("No prior content was recorded for this action")

    product = db.get(models.Product, action.product_id) if action.product_id else None
    if product is None:
        raise OptimizationActionNotRevertible("The product this action changed no longer exists")

    before = _json.loads(action.content_before)
    product.ai_title = before.get("ai_title")
    product.ai_summary = before.get("ai_summary")
    product.ai_caution = before.get("ai_caution")
    if product.ai_copy_source_action_id == action.id:
        product.ai_copy_source_action_id = None

    action.status = "reverted"
    action.reverted_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(action)
    return action


def list_products_by_ids(db: Session, product_ids: list[int], published_only: bool = True) -> list[models.Product]:
    """Same product rows as list_products, but in the exact order given
    (a real, already-decided ranking - see app/content_optimizer.py's
    reorder_homepage action) rather than list_products' own price-change
    ordering. Only pending_review is excluded here (not insufficient_data
    buy_score) - a genuinely popular, real-click product shouldn't be
    hidden from a "trending now" list just because its price history is
    still thin."""
    if not product_ids:
        return []
    query = select(models.Product).where(models.Product.id.in_(product_ids))
    if published_only:
        query = query.where(models.Product.pending_review.is_(False))
    by_id = {p.id: p for p in db.execute(query).scalars()}
    return [by_id[pid] for pid in product_ids if pid in by_id]
