"""2026-10-30 data migration: fixes products filed under the wrong brand.

Two cases, both found in the live catalog:

1. The listing names exactly one other known brand and never its own -
   e.g. "L.A.B. ラブゴルフ LINK.1 パター ... ピンタイプ" filed as PING.
   -> the brand is changed to the one the name actually names.
2. The brand was only ever matched through a shape/colour word that merely
   contains the brand's katakana - "ピン タイプ" / "ピン型" (a putter head
   shape), not PING the maker - and the name names no known brand at all,
   e.g. "WOSS PRO-03 パター ... ピン型". There is no right brand to move it
   to, so it goes back to the admin review queue (pending_review=True),
   which hides it from every public page until an admin approves it again.

Same shape as app/category_migration.py:
- POST /admin/run-brand-migration (routers/admin.py) - the $0 way to run
  this against production (Render's free tier has no shell).

Safe by default: apply=False only builds and returns the plan. Reversible:
the old brand is in plan_lines (saved to the error log on apply), and a
product sent back to review is restored with the existing "承認" button.
Idempotent: a product already fixed has nothing left to do.
"""

import dataclasses
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.brands import BRAND_KEYWORDS, KEYWORD_PATTERNS, keyword_in


@dataclasses.dataclass
class BrandMigrationResult:
    applied: bool
    products_checked: int
    rebranded: int
    sent_to_review: int
    plan_lines: list[str]


def _brands_named(name: str) -> set[str]:
    return {brand for keyword, brand in BRAND_KEYWORDS.items() if keyword_in(keyword, name)}


def _only_loose_match(name: str, brand: str) -> bool:
    """True when `brand` appears in `name` only as a substring the strict
    pattern rejects (the "ピン タイプ" case): a loose hit, never a real one."""
    loose = False
    for keyword, kw_brand in BRAND_KEYWORDS.items():
        if kw_brand != brand:
            continue
        pattern = KEYWORD_PATTERNS.get(keyword)
        if pattern is None:
            if keyword.lower() in name.lower():
                return False  # a real (non-ambiguous) mention
            continue
        if pattern.search(name):
            return False
        if re.search(re.escape(keyword), name):
            loose = True
    return loose


def plan_for(product: models.Product) -> tuple[str, str | None] | None:
    """("rebrand", new_brand) / ("review", None) / None (leave it)."""
    named = _brands_named(product.name)
    if product.brand in named:
        return None
    others = named - {product.brand}
    if len(others) == 1:
        return ("rebrand", next(iter(others)))
    if not named and not product.pending_review and _only_loose_match(product.name, product.brand):
        return ("review", None)
    return None


def run_brand_migration(db: Session, apply: bool) -> BrandMigrationResult:
    products = list(db.execute(select(models.Product).order_by(models.Product.id)).scalars().all())
    plan_lines = [f"対象商品: {len(products)}件"]
    rebrands: list[tuple[models.Product, str, str]] = []
    reviews: list[models.Product] = []
    for product in products:
        plan = plan_for(product)
        if plan is None:
            continue
        if plan[0] == "rebrand":
            rebrands.append((product, product.brand, plan[1]))  # type: ignore[arg-type]
        else:
            reviews.append(product)

    suffix = "" if apply else "予定"
    plan_lines.append(f"\n[ブランド変更{suffix}: {len(rebrands)}件]")
    for product, old, new in rebrands:
        plan_lines.append(f"- id={product.id} {old} -> {new}: {product.name[:60]}")
        if apply:
            product.brand = new
    plan_lines.append(f"\n[確認待ちに戻す{suffix}（非公開）: {len(reviews)}件]")
    for product in reviews:
        plan_lines.append(f"- id={product.id} ({product.brand}と誤認): {product.name[:60]}")
        if apply:
            product.pending_review = True

    if apply and (rebrands or reviews):
        db.commit()

    return BrandMigrationResult(
        applied=apply,
        products_checked=len(products),
        rebranded=len(rebrands),
        sent_to_review=len(reviews),
        plan_lines=plan_lines,
    )
