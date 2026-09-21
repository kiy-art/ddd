from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, pipeline, schemas
from app.auth import require_admin
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/products", response_model=list[schemas.ProductOut])
def list_all_products(db: Session = Depends(get_db)):
    return list(db.execute(select(models.Product).order_by(models.Product.updated_at.desc())).scalars().all())


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


@router.post("/import/csv", response_model=schemas.CsvImportResult)
async def import_csv(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    from app.csv_import import import_csv as do_import

    result = do_import(db, content)

    for product in db.execute(select(models.Product)).scalars().all():
        pipeline.sync_product_analysis(db, product)

    return result


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
    analyzed = 0
    regenerated = 0
    for product in db.execute(select(models.Product)).scalars().all():
        analyzed += 1
        if pipeline.sync_product_analysis(db, product):
            regenerated += 1
    return {
        "prices_updated": price_updated,
        "prices_skipped": price_skipped,
        "products_checked": analyzed,
        "ai_regenerated": regenerated,
    }
