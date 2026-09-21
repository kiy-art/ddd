import datetime
import re

from sqlalchemy import func, select
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


def get_product_by_slug(db: Session, slug: str) -> models.Product | None:
    return db.execute(select(models.Product).where(models.Product.slug == slug)).scalar_one_or_none()


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
    query = query.order_by(models.Product.price_change_percent.asc().nulls_last())
    query = query.offset(offset).limit(limit)
    return list(db.execute(query).scalars().all())


def list_brands(db: Session, published_only: bool = True) -> list[tuple[str, int]]:
    """Distinct brands with a product count, sorted by count desc then name."""
    query = select(models.Product.brand, func.count(models.Product.id)).group_by(models.Product.brand)
    if published_only:
        query = query.where(models.Product.buy_score != "insufficient_data")
    query = query.order_by(func.count(models.Product.id).desc(), models.Product.brand.asc())
    return [(row[0], row[1]) for row in db.execute(query).all()]


def create_product(db: Session, data: schemas.ProductCreate) -> models.Product:
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
        buy_score="insufficient_data",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    if data.initial_price is not None:
        add_price(db, product, data.initial_price)
    return product


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

    result = analysis.analyze_prices(price, pairs, now=recorded_at)

    product.previous_price = product.current_price
    product.current_price = price
    product.average_price = result.average_price
    product.lowest_price = result.lowest_price
    product.price_change_percent = result.price_change_percent
    product.buy_score = result.buy_score
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
    else:
        product.current_price = history[-1].price
        product.previous_price = history[-2].price if len(history) >= 2 else None
    db.commit()
    db.refresh(product)


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
