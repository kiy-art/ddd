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
