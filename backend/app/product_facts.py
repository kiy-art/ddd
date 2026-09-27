"""STEP61: applies the hand-researched maker facts in
backend/data/product_facts.csv (msrp, release date, skill level,
performance type, current-generation flag) to the catalog - the
"上級者向け / 飛び系・やさしさ・操作性" comparison material.

Until now this only existed as a CLI script (scripts/set_product_facts.py),
which Render's free plan has no shell to run - so production products
never got these facts. Same shape as app/category_migration.py: dry-run
by default, applied from an admin button after a preview.

Matching: same brand, and either the product's model_number equals the
row's, or (no model number stored - typical for auto-discovered
products) the row's model name appears in the product name. When several
rows match by name, the LONGEST model wins, so a "G430 MAX" product never
takes the "G430" row's facts. A value already set is never overwritten
(an admin may have corrected it); a missing model_number is filled in,
which also lets popularity ranking matching find the product.
"""

import csv
import dataclasses
import datetime
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models

FACTS_CSV = Path(__file__).resolve().parent.parent / "data" / "product_facts.csv"

SKILL_LABELS = {"beginner": "初心者向け", "all_levels": "幅広いレベル向け", "advanced": "上級者向け"}
PERFORMANCE_LABELS = {"distance": "飛距離重視", "forgiveness": "やさしさ重視", "control": "操作性重視", "balanced": "バランス型"}


@dataclasses.dataclass
class FactRow:
    brand: str
    model_number: str
    msrp: int | None
    release_date: datetime.date | None
    skill_level: str | None
    performance_type: str | None
    is_current_generation: bool | None


@dataclasses.dataclass
class ProductFactsResult:
    applied: bool
    products_checked: int
    updated: int
    plan_lines: list[str]


def _norm(text: str) -> str:
    return re.sub(r"[\s\-_・/()（）]", "", text).lower()


def load_facts(path: Path = FACTS_CSV) -> list[FactRow]:
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            def val(key: str) -> str:
                return (row.get(key) or "").strip()

            generation = val("is_current_generation").lower()
            rows.append(
                FactRow(
                    brand=val("brand"),
                    model_number=val("model_number"),
                    msrp=int(val("msrp")) if val("msrp") else None,
                    release_date=datetime.date.fromisoformat(val("release_date")) if val("release_date") else None,
                    skill_level=val("skill_level") or None,
                    performance_type=val("performance_type") or None,
                    is_current_generation=(generation in ("true", "1", "yes")) if generation else None,
                )
            )
    return [r for r in rows if r.brand and r.model_number]


def match_row(product: models.Product, rows: list[FactRow]) -> FactRow | None:
    same_brand = [r for r in rows if r.brand == product.brand]
    if product.model_number:
        exact = [r for r in same_brand if _norm(r.model_number) == _norm(product.model_number)]
        if exact:
            return exact[0]
    name = _norm(product.name)
    by_name = [r for r in same_brand if _norm(r.model_number) and _norm(r.model_number) in name]
    return max(by_name, key=lambda r: len(_norm(r.model_number)), default=None)


def run_product_facts(db: Session, apply: bool, rows: list[FactRow] | None = None) -> ProductFactsResult:
    rows = rows if rows is not None else load_facts()
    products = list(db.execute(select(models.Product).order_by(models.Product.id)).scalars().all())
    plan_lines = [f"対象商品: {len(products)}件 / 調査済みデータ: {len(rows)}モデル"]
    updated = 0
    changes_lines = []
    for product in products:
        row = match_row(product, rows)
        if row is None:
            continue
        changes: list[tuple[str, object, str]] = []
        if not product.model_number:
            changes.append(("model_number", row.model_number, f"型番 {row.model_number}"))
        if row.msrp is not None and product.msrp is None:
            changes.append(("msrp", row.msrp, f"定価 ¥{row.msrp:,}"))
        if row.release_date is not None and product.release_date is None:
            changes.append(("release_date", row.release_date, f"発売日 {row.release_date.isoformat()}"))
        if row.skill_level and product.skill_level is None:
            changes.append(("skill_level", row.skill_level, SKILL_LABELS.get(row.skill_level, row.skill_level)))
        if row.performance_type and product.performance_type is None:
            changes.append(
                ("performance_type", row.performance_type, PERFORMANCE_LABELS.get(row.performance_type, row.performance_type))
            )
        if row.is_current_generation is not None and product.is_current_generation is None:
            changes.append(
                ("is_current_generation", row.is_current_generation, "現行モデル" if row.is_current_generation else "型落ちモデル")
            )
        if not changes:
            continue
        updated += 1
        changes_lines.append(f"  id={product.id} {product.brand} {product.name}: " + " / ".join(c[2] for c in changes))
        if apply:
            for field, value, _ in changes:
                setattr(product, field, value)
    if apply and updated:
        db.commit()
    plan_lines.append(f"\n[反映{'' if apply else '予定'}: {updated}件]")
    plan_lines.extend(changes_lines or ["  （反映が必要な商品はありません）"])
    return ProductFactsResult(applied=apply, products_checked=len(products), updated=updated, plan_lines=plan_lines)
