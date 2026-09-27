"""STEP58 data migration: moves products that were filed under the wrong
category - a glove, rangefinder or small accessory (pin, marker, fork)
that a club/ball search happened to return - into the category their
name says (see app/categorizer.py for the deliberately conservative rules).

Same shape as app/title_migration.py:
- scripts/category_migration.py - CLI entry point for local/manual use.
- POST /admin/run-category-migration (routers/admin.py) - the only $0 way
  to run this against the production database (Render's free tier has no
  shell).

Safe by default: apply=False only builds and returns the plan, writing
nothing. Idempotent: a product already in its corrected category has
nothing left to do on a second run.

A moved product's Rakuten popularity rank is cleared - it was a rank in
the OLD category's ranking, which says nothing about the new one.
"""

import dataclasses

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import categorizer, models

CATEGORY_LABELS = {
    "driver": "ドライバー",
    "iron": "アイアン",
    "wedge": "ウェッジ",
    "putter": "パター",
    "ball": "ボール",
    "glove": "グローブ",
    "rangefinder": "距離計",
    "other": "その他",
}


@dataclasses.dataclass
class CategoryMigrationResult:
    applied: bool
    products_checked: int
    moved: int
    # Destination category -> count, e.g. {"glove": 3, "other": 5}.
    moved_by_category: dict[str, int]
    plan_lines: list[str]


def run_category_migration(db: Session, apply: bool) -> CategoryMigrationResult:
    products = list(db.execute(select(models.Product).order_by(models.Product.id)).scalars().all())
    plan_lines = [f"対象商品: {len(products)}件"]
    moves: list[tuple[models.Product, str, str]] = []
    for product in products:
        target = categorizer.corrected_category(product.name, product.category)
        if target is not None:
            moves.append((product, product.category, target))

    moved_by_category: dict[str, int] = {}
    plan_lines.append(f"\n[カテゴリ変更{'' if apply else '予定'}: {len(moves)}件]")
    for product, old, new in moves:
        moved_by_category[new] = moved_by_category.get(new, 0) + 1
        plan_lines.append(
            f"  id={product.id} {product.brand} {product.name}: "
            f"{CATEGORY_LABELS.get(old, old)} -> {CATEGORY_LABELS.get(new, new)}"
        )
        if apply:
            product.category = new
            product.popularity_rank = None
            product.popularity_updated_at = None
    if apply and moves:
        db.commit()
    if not moves:
        plan_lines.append("  （変更が必要な商品はありません）")

    return CategoryMigrationResult(
        applied=apply,
        products_checked=len(products),
        moved=len(moves),
        moved_by_category=moved_by_category,
        plan_lines=plan_lines,
    )
