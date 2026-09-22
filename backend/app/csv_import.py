"""CSV price import.

Expected columns: product_name,brand,category,model_number,price,product_url,image_url
Optional columns: msrp,release_date (YYYY-MM-DD),skill_level,performance_type,
is_current_generation (true/false) - manually-researched facts, only ever set
on a newly-created product (see note on Product.msrp), never used to
overwrite an existing row's value.

Any row that fails validation is skipped (not the whole file) and recorded
both in ErrorLog and in the returned CsvImportResult.errors list, per the
"skip on error, keep going" requirement for batch jobs.
"""

import csv
import datetime
import io

from sqlalchemy.orm import Session

from app import crud, schemas
from app.models import CATEGORIES

REQUIRED_COLUMNS = {"product_name", "brand", "category", "price"}


def import_csv(db: Session, content: bytes) -> schemas.CsvImportResult:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        message = f"CSVに必須列がありません: {', '.join(sorted(missing))}"
        crud.create_error_log(db, source="csv_import", message=message)
        return schemas.CsvImportResult(created_products=0, updated_products=0, prices_recorded=0, errors=[message])

    created = 0
    updated = 0
    prices_recorded = 0
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):  # header is line 1
        try:
            name = (row.get("product_name") or "").strip()
            brand = (row.get("brand") or "").strip()
            category = (row.get("category") or "").strip().lower()
            model_number = (row.get("model_number") or "").strip() or None
            price_raw = (row.get("price") or "").strip()
            product_url = (row.get("product_url") or "").strip() or None
            image_url = (row.get("image_url") or "").strip() or None
            msrp_raw = (row.get("msrp") or "").strip()
            msrp = int(float(msrp_raw)) if msrp_raw else None
            release_date_raw = (row.get("release_date") or "").strip()
            release_date = datetime.date.fromisoformat(release_date_raw) if release_date_raw else None
            skill_level = (row.get("skill_level") or "").strip() or None
            performance_type = (row.get("performance_type") or "").strip() or None
            is_current_generation_raw = (row.get("is_current_generation") or "").strip().lower()
            is_current_generation = (
                is_current_generation_raw in ("true", "1", "yes") if is_current_generation_raw else None
            )

            if not name or not brand:
                raise ValueError("product_name / brand は必須です")
            if category not in CATEGORIES:
                raise ValueError(f"category '{category}' は不正です (許可値: {', '.join(CATEGORIES)})")
            if not price_raw:
                raise ValueError("price は必須です")
            price = int(float(price_raw))
            if price <= 0:
                raise ValueError("price は正の数である必要があります")

            existing = crud.find_product_by_identity(db, name, brand, model_number)
            if existing:
                crud.add_price(db, existing, price)
                updated += 1
            else:
                product = crud.create_product(
                    db,
                    schemas.ProductCreate(
                        name=name,
                        brand=brand,
                        category=category,
                        model_number=model_number,
                        image_url=image_url,
                        product_url=product_url,
                        initial_price=price,
                        msrp=msrp,
                        release_date=release_date,
                        skill_level=skill_level,
                        performance_type=performance_type,
                        is_current_generation=is_current_generation,
                    ),
                )
                created += 1
                existing = product
            prices_recorded += 1
        except Exception as exc:  # noqa: BLE001 - want to skip any bad row, not just ValueError
            message = f"{row_num}行目: {exc}"
            errors.append(message)
            crud.create_error_log(db, source="csv_import", message=message)
            continue

    return schemas.CsvImportResult(
        created_products=created,
        updated_products=updated,
        prices_recorded=prices_recorded,
        errors=errors,
    )
