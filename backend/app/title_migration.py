"""STEP15 data migration logic: cleans every product's stored name (see
app/title_cleaner.py) and merges products that turn out to share the same
(brand, cleaned name) - the same identity app/discovery.py dedups new
candidates by, so a raw-title-noise duplicate that slipped in before that
change collapses into one product instead of staying split across several
rows.

Two callers share this same logic, never duplicating it:
- scripts/migrate_clean_titles.py - a CLI entry point for local/manual use.
- POST /admin/run-migration-clean-titles (see routers/admin.py) - added
  because Render's free-tier web service has no shell/SSH access to run
  a script directly, so the admin panel is the only $0 way to run this
  against the production database.

Safe by default: apply=False only builds and returns the plan, writing
nothing. Re-running with apply=True is idempotent - a product already
renamed to its clean form, or already merged, has nothing left to do.
"""

import dataclasses
from typing import Callable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import crud, models, pipeline, title_cleaner


@dataclasses.dataclass
class TitleMigrationResult:
    applied: bool
    products_checked: int
    renamed: int
    merge_groups: int
    products_merged: int
    # Human-readable lines describing exactly what happened (applied=True)
    # or would happen (applied=False) - one line per rename/merge decision,
    # meant for a CLI printout, an ErrorLog entry, or an admin API response.
    plan_lines: list[str]


def _merge_key(product: models.Product, effective_name: str) -> tuple[str, str]:
    return (product.brand.strip().lower(), effective_name.strip().lower())


def _pick_survivor(group: list[models.Product]) -> tuple[models.Product, list[models.Product]]:
    """Prefer an already-published (not pending_review) product, so
    merging never accidentally un-publishes something that was already
    live; then the one with the most recorded price history (the richest,
    most-trusted series); then the oldest (longest-tracked)."""
    ordered = sorted(
        group,
        key=lambda p: (p.pending_review, -len(p.price_history), p.created_at),
    )
    return ordered[0], ordered[1:]


def run_title_cleanup_migration(
    db: Session,
    apply: bool,
    on_progress: Callable[[int, int], None] | None = None,
) -> TitleMigrationResult:
    """`on_progress(current, total)`, when given, is called once per
    product during the (potentially slow, if ANTHROPIC_API_KEY is
    configured) title-cleaning pass - purely an optional progress report
    for the caller (see routers/admin.py + app/progress.py's live
    dashboard); omitting it changes nothing about this function's own
    behavior."""
    plan_lines: list[str] = []
    products = list(db.execute(select(models.Product)).scalars().all())
    plan_lines.append(f"対象商品: {len(products)}件")

    # --- Phase 1: clean every product's stored name ------------------------
    # effective_name is what each product's name WILL be after cleaning,
    # computed up front for every product (whether or not it actually
    # changes) so Phase 2's grouping - and therefore the dry-run preview -
    # reflects the post-clean world even before any row is actually renamed.
    effective_name: dict[int, str] = {}
    rename_plan = []
    for i, product in enumerate(products, start=1):
        cleaned = title_cleaner.clean_product_title(product.name, product.brand, product.category)
        effective_name[product.id] = cleaned
        if cleaned != product.name:
            rename_plan.append((product, product.name, cleaned))
        if on_progress is not None:
            on_progress(i, len(products))

    plan_lines.append(f"\n[リネーム対象: {len(rename_plan)}件]")
    touched_ids: set[int] = set()
    merged_survivor_ids: set[int] = set()
    for product, old_name, new_name in rename_plan:
        plan_lines.append(f"  id={product.id} slug={product.slug}: {old_name!r} -> {new_name!r}")
        if apply:
            product.name = new_name
            touched_ids.add(product.id)
    if apply and rename_plan:
        db.commit()

    # --- Phase 2: merge products that now share the same identity ----------
    groups: dict[tuple[str, str], list[models.Product]] = {}
    for product in products:
        groups.setdefault(_merge_key(product, effective_name[product.id]), []).append(product)
    merge_groups = {key: group for key, group in groups.items() if len(group) > 1}
    products_merged = sum(len(group) - 1 for group in merge_groups.values())  # losers only

    plan_lines.append(f"\n[統合対象: {len(merge_groups)}グループ / 計{sum(len(g) for g in merge_groups.values())}件]")
    for key, group in merge_groups.items():
        survivor, losers = _pick_survivor(group)
        plan_lines.append(
            f"  {key[0]} / {key[1]}: 存続 id={survivor.id} slug={survivor.slug}"
            f" <- 統合 id={[loser.id for loser in losers]}"
        )
        if not apply:
            continue

        for loser in losers:
            # Manually-curated facts (see Product.msrp's own comment): keep
            # the survivor's own value, only fill in from a loser when the
            # survivor doesn't have one - the same never-overwrite-curated-
            # data rule pipeline.fetch_rakuten_prices already applies to
            # image_url/affiliate_url.
            for field in (
                "msrp",
                "release_date",
                "skill_level",
                "performance_type",
                "is_current_generation",
                "image_url",
                "product_url",
                "affiliate_url",
            ):
                if getattr(survivor, field) is None and getattr(loser, field) is not None:
                    setattr(survivor, field, getattr(loser, field))

            # Bulk column updates (not touching the ORM relationship
            # collections directly) so PriceHistory's cascade="all,
            # delete-orphan" can't misread a reassignment as a removal and
            # delete the very rows being moved.
            db.execute(
                update(models.PriceHistory).where(models.PriceHistory.product_id == loser.id).values(product_id=survivor.id)
            )
            db.execute(
                update(models.PriceAlert).where(models.PriceAlert.product_id == loser.id).values(product_id=survivor.id)
            )
            db.execute(
                update(models.ErrorLog).where(models.ErrorLog.product_id == loser.id).values(product_id=survivor.id)
            )
            db.commit()  # reassignment must land before the delete below

            db.delete(loser)
            db.commit()

        touched_ids.add(survivor.id)
        merged_survivor_ids.add(survivor.id)

    # --- Phase 3: recompute stats/AI content for everything touched --------
    # Every renamed-or-merged product's average/lowest/buy_score/forecast/AI
    # blurb must be recomputed from its (possibly now combined) price
    # history and new name, exactly like the daily job already does after
    # any price/name change - see pipeline.sync_product_analysis. A merge
    # survivor additionally needs current_price/previous_price refreshed
    # first (the same crud.recompute_current_price already used after
    # deleting a price row, admin.py's own /admin/prices/{id} DELETE
    # endpoint) - a reassigned loser's price history can include a more
    # recent entry than the survivor's own, and sync_product_analysis only
    # recomputes stats AROUND the existing current_price, it never derives
    # current_price itself.
    if apply and touched_ids:
        plan_lines.append(f"\n[分析・AI説明文を再計算: {len(touched_ids)}件]")
        for product_id in touched_ids:
            product = db.get(models.Product, product_id)
            if product is None:
                continue
            if product_id in merged_survivor_ids:
                crud.recompute_current_price(db, product)
            pipeline.sync_product_analysis(db, product)

    plan_lines.append(
        "\nこれはdry-runです。実際にDBへ反映するには --apply を付けて再実行してください。"
        if not apply
        else "\n適用が完了しました。"
    )

    return TitleMigrationResult(
        applied=apply,
        products_checked=len(products),
        renamed=len(rename_plan),
        merge_groups=len(merge_groups),
        products_merged=products_merged,
        plan_lines=plan_lines,
    )
