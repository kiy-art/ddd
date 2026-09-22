import dataclasses

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, discovery, models, pipeline, popularity, schemas
from app.auth import require_admin
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/products", response_model=list[schemas.ProductOut])
def list_all_products(db: Session = Depends(get_db)):
    return list(db.execute(select(models.Product).order_by(models.Product.updated_at.desc())).scalars().all())


@router.get("/pending-products", response_model=list[schemas.ProductOut])
def list_pending_products(db: Session = Depends(get_db)):
    return crud.list_pending_products(db)


@router.post("/products/{product_id}/approve", response_model=schemas.ProductOut)
def approve_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.approve_product(db, product)


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = crud.create_product(db, data)
    if product.current_price is not None:
        pipeline.sync_product_analysis(db, product)
    return product


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.update_product(db, product, data)


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.delete_product(db, product)
    return None


@router.get("/products/{product_id}/prices", response_model=list[schemas.PriceHistoryOut])
def get_prices(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.get_price_history(db, product_id)


@router.post("/products/{product_id}/prices", response_model=schemas.ProductOut, status_code=201)
def add_price(product_id: int, data: schemas.PriceCreate, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.add_price(db, product, data.price, data.recorded_at)
    pipeline.sync_product_analysis(db, product)
    return product


@router.delete("/prices/{price_history_id}", response_model=schemas.ProductOut)
def delete_price(price_history_id: int, db: Session = Depends(get_db)):
    product_id = crud.delete_price(db, price_history_id)
    if product_id is None:
        raise HTTPException(status_code=404, detail="Price history entry not found")
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.recompute_current_price(db, product)
    if product.current_price is not None:
        pipeline.sync_product_analysis(db, product)
    return product


@router.get("/price-anomalies", response_model=list[schemas.PriceAnomalyOut])
def get_price_anomalies(db: Session = Depends(get_db)):
    return pipeline.find_price_anomalies(db)


@router.post("/price-anomalies/fix", response_model=list[schemas.PriceAnomalyOut])
def fix_price_anomalies(db: Session = Depends(get_db)):
    return pipeline.fix_price_anomalies(db)


@router.get("/price-alerts", response_model=list[schemas.PriceAlertAdminOut])
def list_price_alerts(db: Session = Depends(get_db)):
    """No email delivery is wired up yet (see models.PriceAlert), so this
    is how an admin can currently see who asked to be notified and whether
    their target price has already been reached, until real delivery
    (email/LINE/push) is configured."""
    result = []
    for alert in crud.list_price_alerts(db):
        product = crud.get_product(db, alert.product_id)
        if product is None:
            continue
        triggered = product.current_price is not None and product.current_price <= alert.target_price
        result.append(
            schemas.PriceAlertAdminOut(
                id=alert.id,
                product_id=alert.product_id,
                email=alert.email,
                target_price=alert.target_price,
                created_at=alert.created_at,
                notified_at=alert.notified_at,
                product_name=product.name,
                product_slug=product.slug,
                current_price=product.current_price,
                triggered=triggered,
            )
        )
    return result


@router.post("/import/csv", response_model=schemas.CsvImportResult)
async def import_csv(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    from app.csv_import import import_csv as do_import

    result = do_import(db, content)

    for product in db.execute(select(models.Product)).scalars().all():
        pipeline.sync_product_analysis(db, product)

    return result


@router.get("/contact-messages", response_model=list[schemas.ContactMessageOut])
def list_contact_messages(db: Session = Depends(get_db)):
    return crud.list_contact_messages(db)


@router.post("/contact-messages/{message_id}/read", response_model=schemas.ContactMessageOut)
def mark_contact_message_read(message_id: int, db: Session = Depends(get_db)):
    message = db.get(models.ContactMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return crud.mark_contact_message_read(db, message)


@router.get("/logs", response_model=list[schemas.ErrorLogOut])
def get_logs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return crud.list_error_logs(db, limit=limit, offset=offset)


@router.post("/run-update")
def run_update(db: Session = Depends(get_db)):
    updated = 0
    regenerated = 0
    for product in db.execute(select(models.Product)).scalars().all():
        updated += 1
        if pipeline.sync_product_analysis(db, product):
            regenerated += 1
    return {"products_checked": updated, "ai_regenerated": regenerated}


@router.post("/fetch-rakuten")
def fetch_rakuten(db: Session = Depends(get_db)):
    from app.config import get_settings

    settings = get_settings()
    if not settings.rakuten_app_id or not settings.rakuten_access_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY is not configured "
                f"(app_id_len={len(settings.rakuten_app_id)}, "
                f"access_key_len={len(settings.rakuten_access_key)})"
            ),
        )

    price_updated, price_skipped = pipeline.fetch_rakuten_prices(db)

    # Yahoo is a second, optional price source (unlike Rakuten above, which
    # this endpoint already requires) - only attempted when configured, and
    # a failure here never blocks the rest of the daily job.
    yahoo_updated, yahoo_skipped = 0, 0
    if settings.yahoo_client_id:
        try:
            yahoo_updated, yahoo_skipped = pipeline.fetch_yahoo_prices(db)
        except Exception as exc:  # noqa: BLE001 - Yahoo failing shouldn't fail the whole job
            crud.create_error_log(db, source="price_fetch", message=f"Yahoo fetch failed: {exc}")

    products_discovered, candidates_considered = discovery.discover_new_products(db)
    products_ranked, popularity_categories_checked = popularity.sync_popularity_rankings(db)
    analyzed = 0
    regenerated = 0
    for product in db.execute(select(models.Product)).scalars().all():
        analyzed += 1
        if pipeline.sync_product_analysis(db, product):
            regenerated += 1
    return {
        "prices_updated": price_updated,
        "prices_skipped": price_skipped,
        "yahoo_prices_updated": yahoo_updated,
        "yahoo_prices_skipped": yahoo_skipped,
        "products_discovered": products_discovered,
        "candidates_considered": candidates_considered,
        "products_ranked": products_ranked,
        "popularity_categories_checked": popularity_categories_checked,
        "products_checked": analyzed,
        "ai_regenerated": regenerated,
    }


@router.post("/fetch-yahoo")
def fetch_yahoo(db: Session = Depends(get_db)):
    """Manual trigger for the Yahoo price fetch alone, useful for testing
    without waiting for the next scheduled /fetch-rakuten run."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.yahoo_client_id:
        raise HTTPException(status_code=400, detail="YAHOO_CLIENT_ID is not configured")

    updated, skipped = pipeline.fetch_yahoo_prices(db)
    return {"yahoo_prices_updated": updated, "yahoo_prices_skipped": skipped}


@router.post("/sync-popularity")
def sync_popularity(db: Session = Depends(get_db)):
    """Manual trigger for the same Rakuten-ranking sync that also runs as
    part of the daily /fetch-rakuten job."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.rakuten_app_id:
        raise HTTPException(status_code=400, detail="RAKUTEN_APP_ID is not configured")

    ranked, checked = popularity.sync_popularity_rankings(db)
    return {"products_ranked": ranked, "categories_checked": checked}


@router.post("/discover-products")
def discover_products(db: Session = Depends(get_db)):
    """Manual trigger for the same auto-discovery that also runs as part of
    the daily /fetch-rakuten job, useful for testing without waiting for
    the next scheduled run."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.rakuten_app_id or not settings.rakuten_access_key:
        raise HTTPException(status_code=400, detail="RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY is not configured")

    discovered, considered = discovery.discover_new_products(db)
    return {"products_discovered": discovered, "candidates_considered": considered}


@router.get("/analytics/top-pages", response_model=list[schemas.PageStatOut])
def get_top_pages(days: int = 28, limit: int = 25):
    """Real GA4 pageview/bounce-rate data, for on-demand analysis sessions
    (no automated daily job - see README). Requires GA4_PROPERTY_ID and
    GA4_SERVICE_ACCOUNT_JSON to be set on the backend."""
    from app import analytics_ga4

    try:
        stats = analytics_ga4.get_top_pages(days=days, limit=limit)
    except analytics_ga4.GA4NotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [schemas.PageStatOut(**dataclasses.asdict(s)) for s in stats]
