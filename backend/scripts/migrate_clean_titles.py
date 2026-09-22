"""STEP15 data migration: cleans every existing product's stored name via
app/title_cleaner.py (strips shop promotional noise down to "ブランド＋
型番") and merges any products that turn out to share the same (brand,
cleaned name) - the same identity app/discovery.py now dedups new
candidates by, so a raw-title-noise duplicate that slipped in before this
change collapses into one product instead of staying split across
several rows.

Safe by default: this only PRINTS a plan and makes no database changes
unless --apply is passed. Re-running with --apply is idempotent - a
product already renamed to its clean form, or already merged, has
nothing left to do next time.

Recommended: back up the database before running with --apply. For local
SQLite, copy the .db file. For the production Postgres database on
Render, take a backup/snapshot through Render's dashboard first.

Usage:
    python scripts/migrate_clean_titles.py            # dry run (default)
    python scripts/migrate_clean_titles.py --apply     # writes for real
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import crud, models, pipeline, title_cleaner  # noqa: E402
from app.database import SessionLocal  # noqa: E402


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


def run(apply: bool, db: Session | None = None) -> None:
    """`db`, when given (tests only - see tests/test_migrate_clean_titles.py),
    is used instead of opening a fresh SessionLocal(), and is left open for
    the caller to manage; the CLI entry point below never passes one."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        products = list(db.execute(select(models.Product)).scalars().all())
        print(f"対象商品: {len(products)}件")

        # --- Phase 1: clean every product's stored name -------------------
        # effective_name is what each product's name WILL be after
        # cleaning, computed up front for every product (whether or not
        # it actually changes) so Phase 2's grouping - and therefore this
        # dry run's merge preview - reflects the post-clean world even
        # before any row is actually renamed.
        effective_name: dict[int, str] = {}
        rename_plan = []
        for product in products:
            cleaned = title_cleaner.clean_product_title(product.name, product.brand, product.category)
            effective_name[product.id] = cleaned
            if cleaned != product.name:
                rename_plan.append((product, product.name, cleaned))

        print(f"\n[リネーム対象: {len(rename_plan)}件]")
        touched_ids: set[int] = set()
        merged_survivor_ids: set[int] = set()
        for product, old_name, new_name in rename_plan:
            print(f"  id={product.id} slug={product.slug}: {old_name!r} -> {new_name!r}")
            if apply:
                product.name = new_name
                touched_ids.add(product.id)
        if apply and rename_plan:
            db.commit()

        # --- Phase 2: merge products that now share the same identity -----
        groups: dict[tuple[str, str], list[models.Product]] = {}
        for product in products:
            groups.setdefault(_merge_key(product, effective_name[product.id]), []).append(product)
        merge_groups = {key: group for key, group in groups.items() if len(group) > 1}

        print(f"\n[統合対象: {len(merge_groups)}グループ / 計{sum(len(g) for g in merge_groups.values())}件]")
        for key, group in merge_groups.items():
            survivor, losers = _pick_survivor(group)
            print(
                f"  {key[0]} / {key[1]}: 存続 id={survivor.id} slug={survivor.slug}"
                f" <- 統合 id={[loser.id for loser in losers]}"
            )
            if not apply:
                continue

            for loser in losers:
                # Manually-curated facts (see Product.msrp's own comment):
                # keep the survivor's own value, only fill in from a loser
                # when the survivor doesn't have one - the same
                # never-overwrite-curated-data rule
                # pipeline.fetch_rakuten_prices already applies to
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
                # delete-orphan" can't misread a reassignment as a removal
                # and delete the very rows being moved.
                db.execute(
                    update(models.PriceHistory)
                    .where(models.PriceHistory.product_id == loser.id)
                    .values(product_id=survivor.id)
                )
                db.execute(
                    update(models.PriceAlert)
                    .where(models.PriceAlert.product_id == loser.id)
                    .values(product_id=survivor.id)
                )
                db.execute(
                    update(models.ErrorLog).where(models.ErrorLog.product_id == loser.id).values(product_id=survivor.id)
                )
                db.commit()  # reassignment must land before the delete below

                db.delete(loser)
                db.commit()

            touched_ids.add(survivor.id)
            merged_survivor_ids.add(survivor.id)

        # --- Phase 3: recompute stats/AI content for everything touched ---
        # Every renamed-or-merged product's average/lowest/buy_score/
        # forecast/AI blurb must be recomputed from its (possibly now
        # combined) price history and new name, exactly like the daily job
        # already does after any price/name change - see
        # pipeline.sync_product_analysis. A merge survivor additionally
        # needs current_price/previous_price refreshed first (the same
        # crud.recompute_current_price already used after deleting a price
        # row, admin.py's own /admin/prices/{id} DELETE endpoint) - a
        # reassigned loser's price history can include a more recent entry
        # than the survivor's own, and sync_product_analysis only
        # recomputes stats AROUND the existing current_price, it never
        # derives current_price itself.
        if apply and touched_ids:
            print(f"\n[分析・AI説明文を再計算: {len(touched_ids)}件]")
            for product_id in touched_ids:
                product = db.get(models.Product, product_id)
                if product is None:
                    continue
                if product_id in merged_survivor_ids:
                    crud.recompute_current_price(db, product)
                pipeline.sync_product_analysis(db, product)

        if not apply:
            print("\nこれはdry-runです。実際にDBへ反映するには --apply を付けて再実行してください。")
        else:
            print("\n適用が完了しました。")
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="実際にDBへ変更を書き込む（省略時はdry-run）")
    args = parser.parse_args()
    run(apply=args.apply)
