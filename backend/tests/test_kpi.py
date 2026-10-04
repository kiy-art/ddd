"""STEP71: KPI summary for the weekly management meeting."""

import csv
import datetime
import importlib.util
import pathlib

from app import crud, kpi, models, schemas

NOW = datetime.datetime(2026, 10, 5, 0, 0)


def _product(db, slug, **kw):
    p = crud.create_product(db, schemas.ProductCreate(name=f"{slug} ドライバー", brand="PING", category="driver", initial_price=50000))
    p.slug = slug
    p.buy_score = "good"
    for k, v in kw.items():
        setattr(p, k, v)
    db.commit()
    return p


def test_kpi_summary_counts_real_rows_only(db_session):
    p = _product(db_session, "a", image_url="https://example.com/a.jpg")
    _product(db_session, "b")
    _product(db_session, "c", pending_review=True)
    for days, shop, placement in ((1, "rakuten", "product_card"), (2, "rakuten", "product_sticky_bar"), (10, "yahoo", "store_comparison")):
        db_session.add(models.AffiliateClick(product_id=p.id, shop=shop, placement=placement, created_at=NOW - datetime.timedelta(days=days)))
    for path, imp, clk, pos in (("/products/a", 100, 5, 4.0), ("/products/b", 300, 3, 8.0)):
        db_session.add(models.PageMetricsSnapshot(snapshot_date=datetime.date(2026, 10, 4), path=path, search_impressions=imp, search_clicks=clk, search_position=pos))
    db_session.add(models.PageMetricsSnapshot(snapshot_date=datetime.date(2026, 10, 3), path="/products/a", search_impressions=999, search_clicks=1, search_position=1.0))
    db_session.add(models.PriceAlert(product_id=p.id, email="someone@example.com", target_price=40000))
    db_session.commit()

    s = kpi.kpi_summary(db_session, now=NOW)

    assert s["catalog"]["published_products"] == 2
    assert s["catalog"]["pending_review"] == 1
    assert s["catalog"]["with_image"] == 1
    assert s["shop_clicks"]["last_7d"] == 2 and s["shop_clicks"]["prev_7d"] == 1 and s["shop_clicks"]["total"] == 3
    assert s["shop_clicks"]["last_7d_by_placement"] == {"product_card": 1, "product_sticky_bar": 1}
    # Only the newest snapshot day; position weighted by impressions.
    assert s["search_console"]["snapshot_date"] == "2026-10-04"
    assert s["search_console"]["impressions"] == 400 and s["search_console"]["clicks"] == 8
    assert s["search_console"]["ctr"] == 0.02
    assert s["search_console"]["avg_position"] == 7.0
    assert s["ga4"] is None  # no GA4 rows stored: reported as missing, not zero
    assert s["price_alerts"]["total"] == 1
    assert "someone@example.com" not in str(s)  # counts only, never addresses


def test_kpi_endpoint_requires_admin(client, admin_headers):
    assert client.get("/api/admin/kpi-summary").status_code in (401, 403)
    assert client.get("/api/admin/kpi-summary", headers=admin_headers).status_code == 200


def test_snapshot_script_writes_one_ledger_row_per_day(tmp_path, db_session):
    spec = importlib.util.spec_from_file_location("kpi_snapshot", pathlib.Path(__file__).parents[1] / "scripts" / "kpi_snapshot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = kpi.kpi_summary(db_session, now=NOW)
    day = datetime.date(2026, 10, 5)
    mod.record(summary, day, knowledge=tmp_path)
    mod.record(summary, day, knowledge=tmp_path)  # re-run the same day: replaced, not duplicated
    rows = list(csv.DictReader((tmp_path / "kpi_ledger.csv").open(encoding="utf-8")))
    assert len(rows) == 1 and rows[0]["date"] == "2026-10-05"
    assert (tmp_path / "kpi" / "2026-10-05.json").exists()

    market = list(csv.DictReader((tmp_path / "market_ledger.csv").open(encoding="utf-8")))
    assert [r["date"] for r in market] == ["2026-10-05"] * len(market)
    assert (tmp_path / "auto_pdca_ledger.csv").exists()


def test_market_trend_compares_only_products_priced_in_both_windows(db_session):
    def priced(slug, old, new, category="driver"):
        p = _product(db_session, slug, category=category)
        db_session.query(models.PriceHistory).filter_by(product_id=p.id).delete()  # drop create_product's initial row
        if old is not None:
            db_session.add(models.PriceHistory(product_id=p.id, price=old, recorded_at=NOW - datetime.timedelta(days=30)))
        if new is not None:
            db_session.add(models.PriceHistory(product_id=p.id, price=new, recorded_at=NOW - datetime.timedelta(days=1)))
        db_session.commit()

    priced("down", 50000, 45000)  # -10%
    priced("up", 50000, 52000)  # +4%
    priced("flat", 50000, 50200)  # +0.4%: within ±1%
    priced("no-reference", None, 40000)  # skipped: nothing to compare against
    priced("ball", 5000, 4500, category="ball")

    m = kpi.market_price_trend(db_session, NOW)

    assert m["by_category"]["driver"]["compared"] == 3
    assert (m["by_category"]["driver"]["down"], m["by_category"]["driver"]["up"], m["by_category"]["driver"]["flat"]) == (1, 1, 1)
    assert m["by_category"]["driver"]["median_change_pct"] == 0.4
    assert m["by_category"]["ball"] == {"compared": 1, "down": 1, "up": 0, "flat": 0, "median_change_pct": -10.0}
