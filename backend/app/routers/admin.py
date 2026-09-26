import dataclasses
import queue

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import content_optimizer, crud, daily_report, discovery, models, pipeline, popularity, progress, schemas, title_migration, x_post
from app.auth import require_admin
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

# How often (in products) the analysis stage reports live progress - every
# product would flood the live dashboard once the catalog reaches
# hundreds of products (see STEP12); this still updates several times a
# second on a fast machine and always reports the true final count.
_ANALYSIS_PROGRESS_EVERY = 5


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
    """Email delivery runs automatically as part of /fetch-rakuten (see
    pipeline.send_price_alert_notifications) once RESEND_API_KEY is
    configured. This view still lets an admin see who asked to be notified
    and whether their target price has already been reached, independent
    of whether delivery is configured."""
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


@router.post("/auto-fix-logs", response_model=schemas.AutoFixLogsResult)
def auto_fix_logs(db: Session = Depends(get_db)):
    """The AI War Room's one-tap "AI自動修復" action (CPO/Compliance):
    immediately clears routine info/warning noise (per-product "not found"/
    "price mismatch" notices) and error-level rows older than 3 days,
    instead of waiting for the daily job's own longer automatic retention
    (see fetch_rakuten below). Deliberately does NOT touch error-level rows
    from the last 3 days - this clears accumulated noise, it never hides a
    live, still-current problem from an admin looking at /admin/logs."""
    deleted = crud.cleanup_error_logs(db, {"info": 0, "warning": 0, "error": 3})
    remaining = crud.count_error_logs_by_level(db)
    return schemas.AutoFixLogsResult(
        deleted=deleted, total_deleted=sum(deleted.values()), remaining_by_level=remaining
    )


@router.post("/run-update")
def run_update(db: Session = Depends(get_db)):
    progress.start_run("run_update", "分析・AI説明文の再生成")
    try:
        progress.start_stage("analysis")
        all_products = db.execute(select(models.Product)).scalars().all()
        updated = 0
        regenerated = 0
        for i, product in enumerate(all_products, start=1):
            updated += 1
            if pipeline.sync_product_analysis(db, product):
                regenerated += 1
            if i % _ANALYSIS_PROGRESS_EVERY == 0 or i == len(all_products):
                progress.update_stage_progress("analysis", i, len(all_products))
        progress.finish_stage("analysis", f"対象{updated}件 / AI再生成{regenerated}件")
    finally:
        progress.finish_run()
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

    progress.start_run("fetch_rakuten", "日次バッチ処理")
    try:
        # Every step below runs in its own try/except with a rollback on
        # failure: this endpoint is the one thing the daily cron job calls, so
        # one step blowing up (a network error, a malformed listing, Rakuten
        # rate-limiting mid-run) must never take the later steps down with it -
        # price-alert emails in particular are the most user-facing part of
        # this job and run last, so they're the ones a partial failure earlier
        # would otherwise silently cost. A bare rollback() is required, not
        # optional, before the next step's queries: on Postgres, any query
        # after an unhandled exception on the same session fails with
        # "current transaction is aborted" until the session is rolled back.
        progress.start_stage("rakuten_prices")
        price_updated, price_skipped = 0, 0
        try:
            price_updated, price_skipped = pipeline.fetch_rakuten_prices(
                db, on_progress=lambda cur, total: progress.update_stage_progress("rakuten_prices", cur, total)
            )
        except Exception as exc:  # noqa: BLE001 - keep the rest of the job alive
            db.rollback()
            crud.create_error_log(db, source="price_fetch", message=f"Rakuten fetch failed: {exc}")
        progress.finish_stage("rakuten_prices", f"更新{price_updated}件 / スキップ{price_skipped}件")

        # Yahoo is a second, optional price source (unlike Rakuten above, which
        # this endpoint already requires) - only attempted when configured.
        yahoo_updated, yahoo_skipped = 0, 0
        if settings.yahoo_client_id:
            progress.start_stage("yahoo_prices")
            try:
                yahoo_updated, yahoo_skipped = pipeline.fetch_yahoo_prices(
                    db, on_progress=lambda cur, total: progress.update_stage_progress("yahoo_prices", cur, total)
                )
            except Exception as exc:  # noqa: BLE001 - Yahoo failing shouldn't fail the whole job
                db.rollback()
                crud.create_error_log(db, source="price_fetch", message=f"Yahoo fetch failed: {exc}")
            progress.finish_stage("yahoo_prices", f"更新{yahoo_updated}件 / スキップ{yahoo_skipped}件")

        progress.start_stage("discovery")
        products_discovered, candidates_considered = 0, 0
        try:
            products_discovered, candidates_considered = discovery.discover_new_products(
                db, on_progress=lambda cur, total: progress.update_stage_progress("discovery", cur, total)
            )
        except Exception as exc:  # noqa: BLE001 - discovery failing shouldn't fail the whole job
            db.rollback()
            crud.create_error_log(db, source="discovery", message=f"Discovery failed: {exc}")
        progress.finish_stage("discovery", f"新規{products_discovered}件（候補{candidates_considered}件中）")

        progress.start_stage("popularity")
        products_ranked, popularity_categories_checked = 0, 0
        try:
            products_ranked, popularity_categories_checked = popularity.sync_popularity_rankings(db)
        except Exception as exc:  # noqa: BLE001 - popularity sync failing shouldn't fail the whole job
            db.rollback()
            crud.create_error_log(db, source="popularity", message=f"Popularity sync failed: {exc}")
        progress.finish_stage("popularity", f"反映{products_ranked}件")

        progress.start_stage("analysis")
        all_products = db.execute(select(models.Product)).scalars().all()
        analyzed = 0
        regenerated = 0
        for i, product in enumerate(all_products, start=1):
            analyzed += 1
            try:
                if pipeline.sync_product_analysis(db, product):
                    regenerated += 1
            except Exception as exc:  # noqa: BLE001 - one product's analysis failing shouldn't stop the rest
                db.rollback()
                crud.create_error_log(
                    db, source="analysis", message=f"{product.name}: {exc}", product_id=product.id
                )
            if i % _ANALYSIS_PROGRESS_EVERY == 0 or i == len(all_products):
                progress.update_stage_progress("analysis", i, len(all_products))
        progress.finish_stage("analysis", f"分析{analyzed}件中AI再生成{regenerated}件")

        # Runs after every product's current_price is fresh for this cycle -
        # a no-op when RESEND_API_KEY isn't configured.
        progress.start_stage("price_alerts")
        alerts_sent, alerts_skipped = 0, 0
        try:
            alerts_sent, alerts_skipped = pipeline.send_price_alert_notifications(db)
        except Exception as exc:  # noqa: BLE001 - alert delivery failing shouldn't fail the whole job
            db.rollback()
            crud.create_error_log(db, source="price_alert_email", message=f"Price alert batch failed: {exc}")
        progress.finish_stage("price_alerts", f"送信{alerts_sent}件 / スキップ{alerts_skipped}件")

        # Runs last: an X post about a stale-priced product would be worse than
        # skipping a day, so this only ever runs once everything above (prices,
        # analysis) is as fresh as this cycle can make it. A no-op when the
        # X_* env vars aren't configured.
        progress.start_stage("x_post")
        x_posts_sent, x_posts_skipped = 0, 0
        try:
            x_posts_sent, x_posts_skipped = x_post.post_daily_deals(db)
        except Exception as exc:  # noqa: BLE001 - X posting failing shouldn't fail the whole job
            db.rollback()
            crud.create_error_log(db, source="x_post", message=f"X post batch failed: {exc}")
        progress.finish_stage("x_post", f"投稿{x_posts_sent}件 / スキップ{x_posts_skipped}件")
    finally:
        progress.finish_run()

    # Auto-cleanup: keeps the ErrorLog table from growing unbounded across
    # daily runs without needing an admin to notice and clear it manually
    # (see STEP34 - a "99件のエラー" turned out to be months of untouched
    # accumulation, not a live incident). Routine info/warning entries
    # (per-product "not found"/mismatch notices) are useful for only a
    # couple of weeks; actual error-level entries are kept longer since
    # they're the ones worth investigating. Never allowed to fail the job.
    try:
        crud.cleanup_error_logs(db, {"info": 14, "warning": 14, "error": 30})
    except Exception:  # noqa: BLE001 - cleanup failing must never fail the daily job itself
        db.rollback()

    result = {
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
        "price_alerts_sent": alerts_sent,
        "price_alerts_skipped": alerts_skipped,
        "x_posts_sent": x_posts_sent,
        "x_posts_skipped": x_posts_skipped,
    }

    # A single, always-added "job finished" summary - the most recent
    # ErrorLog row (sorted by created_at desc in /admin/logs), so an admin
    # can see at a glance that today's run actually completed and what it
    # did, without needing to read GitHub Actions' own run history.
    crud.create_error_log(
        db,
        source="daily_job",
        level="info",
        message=(
            "日次更新ジョブ完了: "
            f"楽天更新{price_updated}件/スキップ{price_skipped}件, "
            f"Yahoo更新{yahoo_updated}件/スキップ{yahoo_skipped}件, "
            f"新商品発見{products_discovered}件, "
            f"人気ランキング反映{products_ranked}件, "
            f"分析{analyzed}件中AI再生成{regenerated}件, "
            f"値下がり通知送信{alerts_sent}件/スキップ{alerts_skipped}件, "
            f"X投稿{x_posts_sent}件/スキップ{x_posts_skipped}件"
        ),
    )

    # STEP42: autonomous content-optimization loop (real GA4/Search Console/
    # click data -> rule-based decisions -> Claude-generated rewrites/new
    # guides, each logged to AiOptimizationAction). Runs after prices/
    # analysis/discovery are fresh for this cycle, and before the daily
    # report so the report can summarize what it just did. Never allowed
    # to fail the job - a broken optimization run shouldn't block price
    # updates or the daily report.
    try:
        content_optimizer.run_daily_optimization(db)
    except Exception as exc:  # noqa: BLE001 - optimization failing must never fail the daily job itself
        db.rollback()
        crud.create_error_log(db, source="content_optimizer", message=f"Daily optimization run failed: {exc}")

    # Daily "AI会議" report email (see app/daily_report.py) - runs last so
    # it reports on the daily_job summary row just written above. A no-op
    # (raises DailyReportNotConfigured) when DAILY_REPORT_EMAIL isn't set,
    # same optional-integration pattern as price alerts/X posting.
    try:
        daily_report.send_daily_report(db)
    except daily_report.DailyReportNotConfigured:
        pass
    except Exception as exc:  # noqa: BLE001 - report failing must never fail the daily job itself
        crud.create_error_log(db, source="daily_report", message=f"Daily report email failed: {exc}")

    return result


@router.post("/fetch-yahoo")
def fetch_yahoo(db: Session = Depends(get_db)):
    """Manual trigger for the Yahoo price fetch alone, useful for testing
    without waiting for the next scheduled /fetch-rakuten run."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.yahoo_client_id:
        raise HTTPException(status_code=400, detail="YAHOO_CLIENT_ID is not configured")

    progress.start_run("fetch_yahoo", "Yahoo!価格取得（手動実行）")
    try:
        progress.start_stage("yahoo_prices")
        updated, skipped = pipeline.fetch_yahoo_prices(
            db, on_progress=lambda cur, total: progress.update_stage_progress("yahoo_prices", cur, total)
        )
        progress.finish_stage("yahoo_prices", f"更新{updated}件 / スキップ{skipped}件")
    finally:
        progress.finish_run()
    return {"yahoo_prices_updated": updated, "yahoo_prices_skipped": skipped}


@router.post("/send-price-alerts")
def send_price_alerts(db: Session = Depends(get_db)):
    """Manual trigger for the price-alert email check alone, useful for
    testing without waiting for the next scheduled /fetch-rakuten run."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.resend_api_key:
        raise HTTPException(status_code=400, detail="RESEND_API_KEY is not configured")

    progress.start_run("send_price_alerts", "値下がり通知メール送信（手動実行）")
    try:
        progress.start_stage("price_alerts")
        sent, skipped = pipeline.send_price_alert_notifications(db)
        progress.finish_stage("price_alerts", f"送信{sent}件 / スキップ{skipped}件")
    finally:
        progress.finish_run()
    return {"price_alerts_sent": sent, "price_alerts_skipped": skipped}


@router.post("/send-daily-report")
def send_daily_report_now(db: Session = Depends(get_db)):
    """Manual trigger for the daily AI会議 report email alone, useful for
    testing without waiting for the next scheduled /fetch-rakuten run."""
    try:
        daily_report.send_daily_report(db)
    except daily_report.DailyReportNotConfigured as exc:
        raise HTTPException(status_code=400, detail="DAILY_REPORT_EMAIL is not configured") from exc
    except Exception as exc:  # noqa: BLE001 - surface the real failure to the admin button
        raise HTTPException(status_code=502, detail=f"Failed to send daily report: {exc}") from exc
    return {"sent": True}


@router.post("/post-to-x")
def post_to_x(db: Session = Depends(get_db)):
    """Manual trigger for the same X post that also runs as part of the
    daily /fetch-rakuten job, useful for testing without waiting for the
    next scheduled run."""
    from app.config import get_settings

    settings = get_settings()
    if not (settings.x_api_key and settings.x_api_secret and settings.x_access_token and settings.x_access_token_secret):
        raise HTTPException(status_code=400, detail="X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET is not fully configured")

    progress.start_run("post_to_x", "SNS投稿（手動実行）")
    try:
        progress.start_stage("x_post")
        sent, skipped = x_post.post_daily_deals(db)
        progress.finish_stage("x_post", f"投稿{sent}件 / スキップ{skipped}件")
    finally:
        progress.finish_run()
    return {"x_posts_sent": sent, "x_posts_skipped": skipped}


@router.get("/x-post-preview")
def x_post_preview(db: Session = Depends(get_db)):
    """Read-only preview of the ready-to-paste X post text (same selection/
    wording post_daily_deals would tweet) - for manually copying onto X
    since the free API tier no longer allows posting (402). Does not
    require X credentials to be configured; `text` is null when no product
    genuinely qualifies today (never a fabricated placeholder)."""
    return {"text": x_post.build_manual_post_text(db)}


@router.post("/sync-popularity")
def sync_popularity(db: Session = Depends(get_db)):
    """Manual trigger for the same Rakuten-ranking sync that also runs as
    part of the daily /fetch-rakuten job."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.rakuten_app_id:
        raise HTTPException(status_code=400, detail="RAKUTEN_APP_ID is not configured")

    progress.start_run("sync_popularity", "人気ランキング同期（手動実行）")
    try:
        progress.start_stage("popularity")
        ranked, checked = popularity.sync_popularity_rankings(db)
        progress.finish_stage("popularity", f"反映{ranked}件（{checked}カテゴリ確認）")
    finally:
        progress.finish_run()
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

    progress.start_run("discover_products", "商品自動検出（手動実行）")
    try:
        progress.start_stage("discovery")
        discovered, considered = discovery.discover_new_products(
            db, on_progress=lambda cur, total: progress.update_stage_progress("discovery", cur, total)
        )
        progress.finish_stage("discovery", f"新規{discovered}件（候補{considered}件中）")
    finally:
        progress.finish_run()
    return {"products_discovered": discovered, "candidates_considered": considered}


@router.post("/run-migration-clean-titles")
def run_migration_clean_titles(dry_run: bool = False, db: Session = Depends(get_db)):
    """Runs the STEP15 title-cleanup + duplicate-merge migration
    (app/title_migration.py, same logic as scripts/migrate_clean_titles.py)
    against the live database. Added as a STEP16 workaround: Render's free
    tier has no shell/SSH access to run the script directly, and this
    endpoint is the $0 alternative - no paid plan required.

    Pass ?dry_run=true to preview the plan (renames/merges that WOULD
    happen) without writing anything - the same safety default the CLI
    script itself has, just opt-in here since a single admin-panel button
    press is expected to actually apply by default."""
    progress.start_run("run_migration_clean_titles", "商品名クレンジング・重複統合（手動実行）")
    try:
        progress.start_stage("title_cleanup")
        result = title_migration.run_title_cleanup_migration(
            db,
            apply=not dry_run,
            on_progress=lambda cur, total: progress.update_stage_progress("title_cleanup", cur, total),
        )
        progress.finish_stage(
            "title_cleanup",
            f"対象{result.products_checked}件 / リネーム{result.renamed}件 / "
            f"統合{result.merge_groups}グループ（{result.products_merged}件）"
            + ("（dry-run）" if dry_run else ""),
        )
    finally:
        progress.finish_run()

    crud.create_error_log(
        db,
        source="title_cleanup",
        level="info",
        message="\n".join(result.plan_lines),
    )

    return {
        "applied": result.applied,
        "products_checked": result.products_checked,
        "renamed": result.renamed,
        "merge_groups": result.merge_groups,
        "products_merged": result.products_merged,
    }


@router.get("/live")
def live_updates():
    """Server-Sent Events stream of the current (or most recently
    finished) job's progress - see app/progress.py. A plain `fetch()` +
    ReadableStream reader on the frontend, not the browser's native
    EventSource: EventSource can't send the Authorization header this
    admin API requires, and this project doesn't use cookies for admin
    auth (see app/auth.py)."""

    def event_stream():
        sub_id, q = progress.subscribe()
        try:
            snapshot = progress.get_snapshot_sse_line()
            if snapshot is not None:
                yield snapshot
            while True:
                try:
                    yield q.get(timeout=15)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            progress.unsubscribe(sub_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Render's edge proxy (and any other intermediary nginx-style
            # buffering proxy) would otherwise hold the whole response
            # until it closes, defeating the point of a live stream.
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


@router.get("/affiliate-clicks/summary", response_model=schemas.AffiliateClickSummary)
def get_affiliate_click_summary(db: Session = Depends(get_db)):
    """Real first-party click counts recorded by POST /track/affiliate-click
    (see models.AffiliateClick) - total, per-shop breakdown, top-clicked
    products, and a recent feed. Powers the AI Team dashboard's metrics and
    the CRO AI persona's data-driven commentary; never estimated."""
    return crud.get_affiliate_click_summary(db)


@router.post("/run-content-optimization", response_model=schemas.ContentOptimizationRunResult)
def run_content_optimization_now(db: Session = Depends(get_db)):
    """Manual trigger for the same STEP42 content-optimization run (real
    GA4/Search Console/click snapshot -> rule-based decisions -> Claude-
    generated rewrites/new guides) that also runs at the end of the daily
    /fetch-rakuten job - useful for testing without waiting for the next
    scheduled run. Rewrites/new guides call the Claude API (real cost,
    capped at content_optimizer.DAILY_ACTION_CAP actions)."""
    result = content_optimizer.run_daily_optimization(db)
    return schemas.ContentOptimizationRunResult(
        snapshot_captured=result.ga4_available or result.search_console_available,
        actions_evaluated=result.actions_evaluated,
        actions_applied=len(result.actions),
        actions=result.actions,
    )


@router.get("/optimization-actions", response_model=list[schemas.AiOptimizationActionOut])
def list_optimization_actions(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """The STEP42 "ナレッジ" log: every autonomous content/layout decision,
    why it was made, what changed, and (once enough time has passed) the
    real measured effect. Powers the admin optimization panel and the
    War Room chat's real-data commentary."""
    return crud.list_optimization_actions(db, limit=limit, offset=offset)


@router.post("/optimization-actions/{action_id}/revert", response_model=schemas.AiOptimizationActionOut)
def revert_optimization_action(action_id: int, db: Session = Depends(get_db)):
    """Restores a rewritten product's previous ai_title/ai_summary/
    ai_caution from the action's own content_before snapshot - the
    concrete undo path for an AI decision that turned out to be wrong."""
    try:
        return crud.revert_optimization_action(db, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.OptimizationActionNotRevertible as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
