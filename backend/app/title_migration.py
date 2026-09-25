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

STEP22: a merge group is several separate Product rows that all turned out
to be the exact same model, discovered independently from different Rakuten
shops - so BEFORE merging, each one's own current_price/product_url/
affiliate_url/image_url is a real, different shop's own offer. The merged
survivor now needs to represent "the cheapest of those shops", not
whichever offer happens to have the most recently recorded price - see
_pick_cheapest_offer and its use in the merge loop below. This is
deliberately different from the msrp/release_date/etc fields just below it,
which keep following the older "only fill in when the survivor doesn't
already have one" rule (see their own comment) - those are manually-
curated facts about the PRODUCT, unrelated to which shop is cheapest today.
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
    most-trusted series); then the oldest (longest-tracked).

    This decides which ROW (id/slug/created_at) survives, for site/SEO
    stability - a separate question from which shop's OFFER (price/url/
    image) the survivor should display, which _pick_cheapest_offer below
    decides instead."""
    ordered = sorted(
        group,
        key=lambda p: (p.pending_review, -len(p.price_history), p.created_at),
    )
    return ordered[0], ordered[1:]


@dataclasses.dataclass
class _Offer:
    product_id: int
    price: int
    product_url: str | None
    affiliate_url: str | None
    image_url: str | None


def _pick_cheapest_offer(group: list[models.Product]) -> _Offer | None:
    """The lowest current_price among every product in the merge group -
    each one really is a different shop's own listing for the same model
    (see module docstring) - or None if nobody in the group has a price
    yet. Captured as plain values (not the ORM objects themselves) since
    the caller deletes the losing rows before this offer gets applied to
    the survivor - an ORM instance would raise on access once its row is
    gone."""
    priced = [p for p in group if p.current_price is not None]
    if not priced:
        return None
    cheapest = min(priced, key=lambda p: p.current_price)
    return _Offer(
        product_id=cheapest.id,
        price=cheapest.current_price,
        product_url=cheapest.product_url,
        affiliate_url=cheapest.affiliate_url,
        image_url=cheapest.image_url,
    )


def _pick_cheapest_yahoo_offer(group: list[models.Product]) -> tuple[int, str | None] | None:
    """Same "cheapest real offer among the group" rule as
    _pick_cheapest_offer, applied to the independent Yahoo! price/url pair
    (see models.Product.yahoo_price's own comment) so the store-comparison
    table stays honest about the group's real cheapest Yahoo listing too,
    not just whichever member happened to survive."""
    priced = [p for p in group if p.yahoo_price is not None]
    if not priced:
        return None
    cheapest = min(priced, key=lambda p: p.yahoo_price)
    return cheapest.yahoo_price, cheapest.yahoo_url


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
    price_synced_ids: set[int] = set()
    for key, group in merge_groups.items():
        survivor, losers = _pick_survivor(group)
        # STEP22: captured from the group's pre-merge state, before any
        # loser is deleted below (see _pick_cheapest_offer's own comment on
        # why these must be plain values, not the ORM objects themselves).
        cheapest_offer = _pick_cheapest_offer(group)
        cheapest_yahoo = _pick_cheapest_yahoo_offer(group)

        if cheapest_offer is not None:
            plan_lines.append(
                f"  {key[0]} / {key[1]}: 存続 id={survivor.id} slug={survivor.slug}"
                f" <- 統合 id={[loser.id for loser in losers]}"
                f"（最安値: id={cheapest_offer.product_id} ¥{cheapest_offer.price:,}）"
            )
        else:
            plan_lines.append(
                f"  {key[0]} / {key[1]}: 存続 id={survivor.id} slug={survivor.slug}"
                f" <- 統合 id={[loser.id for loser in losers]}（価格情報なし）"
            )
        if not apply:
            continue

        if cheapest_offer is not None:
            survivor.previous_price = survivor.current_price
            survivor.current_price = cheapest_offer.price
            survivor.product_url = cheapest_offer.product_url
            survivor.affiliate_url = cheapest_offer.affiliate_url
            survivor.image_url = cheapest_offer.image_url
            price_synced_ids.add(survivor.id)
        if cheapest_yahoo is not None:
            survivor.yahoo_price, survivor.yahoo_url = cheapest_yahoo

        for loser in losers:
            # Manually-curated facts (see Product.msrp's own comment): keep
            # the survivor's own value, only fill in from a loser when the
            # survivor doesn't have one. Deliberately NOT current_price/
            # product_url/affiliate_url/image_url/yahoo_price/yahoo_url
            # anymore (STEP22) - those now always follow the group's
            # cheapest real offer, set above, not a fill-blank rule.
            for field in (
                "msrp",
                "release_date",
                "skill_level",
                "performance_type",
                "is_current_generation",
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
    # survivor's current_price/previous_price were already set above from
    # the group's cheapest real offer (STEP22) when one existed
    # (price_synced_ids) - crud.recompute_current_price's own "latest
    # recorded row wins" rule is only used as a fallback for the rare group
    # where nobody had a price at all, matching what a plain rename (no
    # merge) or an admin deleting a single bad price row already do.
    if apply and touched_ids:
        plan_lines.append(f"\n[分析・AI説明文を再計算: {len(touched_ids)}件]")
        for product_id in touched_ids:
            product = db.get(models.Product, product_id)
            if product is None:
                continue
            if product_id in merged_survivor_ids and product_id not in price_synced_ids:
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
