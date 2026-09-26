import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import consumables_merchandiser, crud, models, schemas
from app.database import get_db
from app.models import CATEGORIES

router = APIRouter(tags=["public"])


def _guide_to_schema(guide: models.GuideArticle) -> schemas.GuideArticleOut:
    sections = [schemas.GuideSectionSchema(**s) for s in json.loads(guide.sections_json)]
    related = [c.strip() for c in (guide.related_categories or "").split(",") if c.strip()]
    return schemas.GuideArticleOut(
        slug=guide.slug,
        title=guide.title,
        description=guide.description,
        published_at=guide.published_at,
        related_categories=related,
        featured_kind=guide.featured_kind,
        featured_category=guide.featured_category,
        featured_heading=guide.featured_heading,
        featured_limit=guide.featured_limit,
        sections=sections,
        source=guide.source,
    )


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


@router.get("/brands/{brand}/price-stats", response_model=schemas.BrandPriceStats)
def get_brand_price_stats(brand: str, db: Session = Depends(get_db)):
    return crud.get_brand_price_stats(db, brand)


@router.get("/products/{slug}", response_model=schemas.ProductDetailOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = crud.get_product_by_slug(db, slug, exclude_pending=True)
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


@router.post("/contact", response_model=schemas.ContactMessageOut, status_code=201)
def submit_contact_message(data: schemas.ContactMessageCreate, db: Session = Depends(get_db)):
    """No email is sent - see models.ContactMessage - this only records the
    message for an admin to read via GET /admin/contact-messages."""
    return crud.create_contact_message(db, data)


@router.post("/track/affiliate-click", status_code=204)
def track_affiliate_click(data: schemas.AffiliateClickCreate, db: Session = Depends(get_db)):
    """First-party record of a real outbound click (Amazon/Rakuten/Yahoo!/
    official) - see models.AffiliateClick. Fire-and-forget from the
    frontend (see lib/affiliateTracking.ts): never blocks or affects the
    actual navigation, so this endpoint stays permissive - an unknown
    product_id is simply stored as-is rather than rejected, since the
    click itself is still real even if a product was later deleted."""
    crud.create_affiliate_click(db, data)
    return None


@router.post("/products/{slug}/alerts", response_model=schemas.PriceAlertOut, status_code=201)
def create_price_alert(slug: str, data: schemas.PriceAlertCreate, db: Session = Depends(get_db)):
    """Records a "notify me below ¥X" request. No email is sent yet - see
    models.PriceAlert for why - so this only confirms the request was saved."""
    product = crud.get_product_by_slug(db, slug, exclude_pending=True)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.create_price_alert(db, product, data)


@router.get("/homepage/trending", response_model=schemas.TrendingProductsOut)
def get_trending_products(db: Session = Depends(get_db)):
    """The most recent day's real click-based "注目ギア" pick (see
    app/content_optimizer.py's reorder_homepage action) - a stored, dated
    decision rather than a live-recomputed query, so it stays stable for
    the day and has a real "before" to measure effect against later.
    Returns an empty list (never a fabricated/padded one) when no such
    decision has been made yet (e.g. zero real clicks recorded so far)."""
    action = db.execute(
        select(models.AiOptimizationAction)
        .where(models.AiOptimizationAction.action_type == "reorder_homepage")
        .order_by(models.AiOptimizationAction.created_at.desc())
    ).scalars().first()
    if action is None or not action.content_after:
        return schemas.TrendingProductsOut(decision_basis=None, products=[])

    product_ids = json.loads(action.content_after).get("product_ids", [])
    if not product_ids:
        return schemas.TrendingProductsOut(decision_basis=action.decision_basis, products=[])

    products = crud.list_products_by_ids(db, product_ids, published_only=True)
    return schemas.TrendingProductsOut(decision_basis=action.decision_basis, products=products)


@router.get("/guides", response_model=list[schemas.GuideArticleOut])
def list_ai_guides(db: Session = Depends(get_db)):
    """AI-authored guide articles only (see app/content_optimizer.py's
    new_guide action / models.GuideArticle) - the site's original,
    hand/AI-authored guides still live as static content in
    frontend/lib/guides.ts and aren't served here."""
    return [_guide_to_schema(g) for g in crud.list_guide_articles(db)]


@router.get("/guides/{slug}", response_model=schemas.GuideArticleOut)
def get_ai_guide(slug: str, db: Session = Depends(get_db)):
    guide = crud.get_guide_article_by_slug(db, slug)
    if guide is None:
        raise HTTPException(status_code=404, detail="Guide not found")
    return _guide_to_schema(guide)


@router.get("/consumables/picks", response_model=schemas.ConsumablePicksOut)
def consumable_picks(limit: int = 6, exclude_product_id: int | None = None, db: Session = Depends(get_db)):
    """STEP52 "AI厳選・高コスパ消耗品": 3-6 consumables picked for the current
    season from real, fresh prices (see app/consumables_merchandiser.py).
    Read-only and cheap (two small queries) - safe to render on every page."""
    season, events, picks = consumables_merchandiser.select_picks(db, exclude_product_id=exclude_product_id, limit=limit)
    return schemas.ConsumablePicksOut(
        season=season,
        season_label=consumables_merchandiser.SEASONS[season],
        sale_events=[e.name for e in events],
        picks=[
            schemas.ConsumablePickOut(
                key=p.key,
                kind=p.kind,
                kind_label=consumables_merchandiser.KIND_LABELS.get(p.kind, "消耗品"),
                brand=p.brand,
                name=p.name,
                current_price=p.current_price,
                reference_price=p.reference.price if p.reference else None,
                reference_label=p.reference.label if p.reference else None,
                discount_percent=p.discount_percent,
                savings_yen=p.savings_yen,
                discount_badge=p.discount_badge,
                savings_text=p.savings_text,
                ai_tag=p.ai_tag,
                micro_copy=p.micro_copy,
                image_url=p.image_url,
                rakuten_url=p.rakuten_url,
                amazon_query=p.amazon_query,
                product_slug=p.product_slug,
                product_id=p.product_id,
                price_updated_at=p.price_updated_at,
            )
            for p in picks
        ],
    )
