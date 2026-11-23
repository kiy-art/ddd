import datetime

from app import crud, schemas


def _published(db, i, **kw):
    p = crud.create_product(
        db, schemas.ProductCreate(name=f"テスト ドライバー {i}", brand="PING", category="driver", initial_price=50000 + i)
    )
    p.buy_score = "good"
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_stats_counts_every_published_product_not_one_page(client, db_session):
    for i in range(60):
        _published(db_session, i)
    _published(db_session, 100, buy_score="insufficient_data")  # hidden on the site
    _published(db_session, 101, pending_review=True)  # hidden on the site
    db_session.commit()

    assert len(client.get("/api/products").json()) == 50  # one page only
    assert client.get("/api/stats").json()["published_products"] == 60


def test_sitemap_products_lists_all_published_slugs(client, db_session):
    for i in range(60):
        _published(db_session, i)
    hidden = _published(db_session, 100, pending_review=True)
    db_session.commit()

    rows = client.get("/api/sitemap/products").json()
    slugs = {r["slug"] for r in rows}
    assert len(slugs) == 60
    assert hidden.slug not in slugs
    assert all(r["updated_at"] for r in rows)
    assert all(r["price_changed_at"] is None for r in rows)  # no price change recorded yet


def test_sitemap_products_price_changed_at_is_first_row_after_last_other_price(client, db_session):
    base = datetime.datetime(2026, 11, 1, 1, 0, 0)
    day = datetime.timedelta(days=1)
    changed = _published(db_session, 1)  # initial row is 50001 (recorded "now")
    unchanged = _published(db_session, 2)
    db_session.commit()
    # Explicit history (oldest first): 50001 -> 40000 on day 2, then the same price again.
    for row in list(changed.price_history) + list(unchanged.price_history):
        row.recorded_at = base
    db_session.commit()
    crud.add_price(db_session, changed, 40000, recorded_at=base + day)
    crud.add_price(db_session, changed, 40000, recorded_at=base + 2 * day)  # same price: must not move the date
    crud.add_price(db_session, unchanged, 50002, recorded_at=base + day)  # same as its current price

    rows = {r["slug"]: r for r in client.get("/api/sitemap/products").json()}
    assert rows[changed.slug]["price_changed_at"].startswith("2026-11-02T01:00:00")
    assert rows[unchanged.slug]["price_changed_at"] is None


def test_sitemap_products_price_changed_at_after_price_returns(client, db_session):
    base = datetime.datetime(2026, 11, 1, 1, 0, 0)
    day = datetime.timedelta(days=1)
    product = _published(db_session, 3)  # 50003
    db_session.commit()
    product.price_history[0].recorded_at = base
    db_session.commit()
    crud.add_price(db_session, product, 45000, recorded_at=base + day)
    crud.add_price(db_session, product, 50003, recorded_at=base + 2 * day)  # back to the old price

    rows = {r["slug"]: r for r in client.get("/api/sitemap/products").json()}
    assert rows[product.slug]["price_changed_at"].startswith("2026-11-03T01:00:00")


def test_accessory_category_pages_list_approved_products_without_a_score_yet(client, db_session):
    glove = crud.create_product(
        db_session, schemas.ProductCreate(name="ウェザーソフ グローブ", brand="FootJoy", category="glove", initial_price=1380)
    )
    pending = crud.create_product(
        db_session, schemas.ProductCreate(name="テスト グローブ", brand="FootJoy", category="glove", initial_price=1500)
    )
    pending.pending_review = True
    unscored_driver = crud.create_product(
        db_session, schemas.ProductCreate(name="テスト ドライバー", brand="PING", category="driver", initial_price=60000)
    )
    db_session.commit()
    assert glove.buy_score == "insufficient_data"

    gloves = [p["slug"] for p in client.get("/api/categories/glove").json()]
    assert gloves == [glove.slug]  # approved but unscored: listed; pending: never
    # Club pages keep the "scored products only" rule.
    assert unscored_driver.slug not in [p["slug"] for p in client.get("/api/categories/driver").json()]


def test_price_alerts_are_only_offered_when_visitor_mail_can_be_delivered(client, monkeypatch):
    from app.config import get_settings

    cases = [
        ("", "PAR. <alerts@par-gear.com>", "true", False),  # no API key
        ("re_test", "PAR. <onboarding@resend.dev>", "true", False),  # shared test sender: owner-only delivery
        ("re_test", "PAR. <alerts@par-gear.com>", "false", False),  # STEP74: privacy policy not yet published
        ("re_test", "PAR. <alerts@par-gear.com>", "true", True),
    ]
    for key, sender, published, expected in cases:
        monkeypatch.setenv("RESEND_API_KEY", key)
        monkeypatch.setenv("RESEND_FROM_EMAIL", sender)
        monkeypatch.setenv("PRIVACY_POLICY_PUBLISHED", published)
        get_settings.cache_clear()
        assert client.get("/api/stats").json()["price_alerts_enabled"] is expected
    get_settings.cache_clear()
