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
    assert client.get("/api/stats").json() == {"published_products": 60}


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
