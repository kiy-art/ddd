import datetime
import re

from sqlalchemy import select
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
    buy_score: str | None = None,
    published_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Product]:
    query = select(models.Product)
    if category:
        query = query.where(models.Product.category == category)
    if buy_score:
        query = query.where(models.Product.buy_score == buy_score)
    if published_only:
        query = query.where(models.Product.buy_score != "insufficient_data")
    query = query.order_by(models.Product.price_change_percent.asc().nulls_last())
    query = query.offset(offset).limit(limit)
    return list(db.execute(query).scalars().all())


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
