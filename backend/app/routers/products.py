from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.models import CATEGORIES

router = APIRouter(tags=["public"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    category: str | None = None,
    brand: str | None = None,
    buy_score: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return crud.list_products(
        db,
        category=category,
        brand=brand,
        buy_score=buy_score,
        published_only=True,
        limit=limit,
        offset=offset,
    )


@router.get("/brands", response_model=list[schemas.BrandSummary])
def list_brands(db: Session = Depends(get_db)):
    return [schemas.BrandSummary(brand=brand, product_count=count) for brand, count in crud.list_brands(db)]


@router.get("/brands/{brand}", response_model=list[schemas.ProductOut])
def list_by_brand(brand: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return crud.list_products(db, brand=brand, published_only=True, limit=limit, offset=offset)


@router.get("/products/{slug}", response_model=schemas.ProductDetailOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = crud.get_product_by_slug(db, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/categories/{category}", response_model=list[schemas.ProductOut])
def list_by_category(category: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail="Unknown category")
    return crud.list_products(
        db, category=category, published_only=True, limit=limit, offset=offset
    )


@router.post("/products/{slug}/alerts", response_model=schemas.PriceAlertOut, status_code=201)
def create_price_alert(slug: str, data: schemas.PriceAlertCreate, db: Session = Depends(get_db)):
    """Records a "notify me below ¥X" request. No email is sent yet - see
    models.PriceAlert for why - so this only confirms the request was saved."""
    product = crud.get_product_by_slug(db, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.create_price_alert(db, product, data)
