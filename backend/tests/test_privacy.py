"""STEP75 (approval #003): unsubscribe links, token backfill and the
retention purge."""

import datetime

from sqlalchemy import create_engine, inspect, text

from app import crud, models, retention, schemas


def _product(db):
    product = models.Product(name="G430 Iron", brand="PING", category="iron", slug="g430-iron", current_price=60000)
    db.add(product)
    db.commit()
    return product


def _alert(db, product, address="buyer@example.com"):
    return crud.create_price_alert(db, product, schemas.PriceAlertCreate(email=address, target_price=50000, consent=True))


def test_new_alerts_get_an_unguessable_token_and_consent_time(db_session):
    product = _product(db_session)
    a, b = _alert(db_session, product), _alert(db_session, product)
    assert a.unsubscribe_token and b.unsubscribe_token
    assert a.unsubscribe_token != b.unsubscribe_token
    assert len(a.unsubscribe_token) >= 40
    assert a.consented_at is not None


def test_backfill_gives_each_old_row_its_own_token(db_session):
    product = _product(db_session)
    for address in ("a@example.com", "b@example.com"):
        db_session.add(models.PriceAlert(product_id=product.id, email=address, target_price=1))
    db_session.commit()

    assert crud.backfill_unsubscribe_tokens(db_session) == 2
    tokens = {a.unsubscribe_token for a in crud.list_price_alerts(db_session)}
    assert len(tokens) == 2 and None not in tokens
    assert crud.backfill_unsubscribe_tokens(db_session) == 0  # idempotent


def test_unsubscribe_get_is_read_only_and_masks_the_address(client, db_session):
    product = _product(db_session)
    alert = _alert(db_session, product)

    resp = client.get(f"/api/alerts/unsubscribe/{alert.unsubscribe_token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_slug"] == "g430-iron"
    assert body["masked_email"] == "bu***@example.com"
    assert "buyer@example.com" not in resp.text
    assert len(crud.list_price_alerts(db_session)) == 1  # nothing stopped by a GET


def test_unsubscribe_post_deletes_one_or_all_for_the_address(client, db_session):
    product = _product(db_session)
    first = _alert(db_session, product)
    _alert(db_session, product)
    _alert(db_session, product, address="other@example.com")
    first_token = first.unsubscribe_token

    resp = client.post(f"/api/alerts/unsubscribe/{first_token}", json={"all_for_email": False})
    assert resp.json() == {"deleted": 1}
    assert client.get(f"/api/alerts/unsubscribe/{first_token}").status_code == 404

    remaining = [a for a in crud.list_price_alerts(db_session) if a.email == "buyer@example.com"]
    resp = client.post(f"/api/alerts/unsubscribe/{remaining[0].unsubscribe_token}", json={"all_for_email": True})
    assert resp.json() == {"deleted": 1}
    assert [a.email for a in crud.list_price_alerts(db_session)] == ["other@example.com"]


def test_unknown_token_is_404(client):
    assert client.get("/api/alerts/unsubscribe/not-a-token").status_code == 404
    assert client.post("/api/alerts/unsubscribe/not-a-token", json={}).status_code == 404


def test_retention_purge_dry_run_counts_and_apply_deletes(db_session):
    now = datetime.datetime(2026, 10, 5)
    product = _product(db_session)
    rows = [
        # sent 91 days ago -> purge; sent 89 days ago -> keep
        models.PriceAlert(product_id=product.id, email="a@x.jp", target_price=1, created_at=now - datetime.timedelta(days=120), notified_at=now - datetime.timedelta(days=91)),
        models.PriceAlert(product_id=product.id, email="b@x.jp", target_price=1, created_at=now - datetime.timedelta(days=120), notified_at=now - datetime.timedelta(days=89)),
        # never sent: 366 days -> purge; 364 days -> keep
        models.PriceAlert(product_id=product.id, email="c@x.jp", target_price=1, created_at=now - datetime.timedelta(days=366)),
        models.PriceAlert(product_id=product.id, email="d@x.jp", target_price=1, created_at=now - datetime.timedelta(days=364)),
        # contact: read 366 days ago -> purge; unread for 2 years -> keep
        models.ContactMessage(email="e@x.jp", message="hi", created_at=now - datetime.timedelta(days=400), read_at=now - datetime.timedelta(days=366)),
        models.ContactMessage(email="f@x.jp", message="hi", created_at=now - datetime.timedelta(days=730)),
    ]
    db_session.add_all(rows)
    db_session.commit()

    preview = retention.run_retention_purge(db_session, apply=False, now=now)
    assert (preview.applied, preview.price_alerts, preview.contact_messages) == (False, 2, 1)
    assert not any("@" in line for line in preview.plan_lines)  # no addresses in the log
    assert len(crud.list_price_alerts(db_session)) == 4  # dry run wrote nothing

    done = retention.run_retention_purge(db_session, apply=True, now=now)
    assert (done.price_alerts, done.contact_messages) == (2, 1)
    assert sorted(a.email for a in crud.list_price_alerts(db_session)) == ["b@x.jp", "d@x.jp"]
    assert [m.email for m in db_session.query(models.ContactMessage).all()] == ["f@x.jp"]


def test_retention_purge_endpoint_defaults_to_dry_run(client, admin_headers, db_session):
    product = _product(db_session)
    db_session.add(models.PriceAlert(product_id=product.id, email="a@x.jp", target_price=1, created_at=datetime.datetime(2020, 1, 1)))
    db_session.commit()

    resp = client.post("/api/admin/run-retention-purge", headers=admin_headers)
    assert resp.json()["applied"] is False and resp.json()["price_alerts"] == 1
    assert len(crud.list_price_alerts(db_session)) == 1

    resp = client.post("/api/admin/run-retention-purge?dry_run=false", headers=admin_headers)
    assert resp.json()["applied"] is True
    assert crud.list_price_alerts(db_session) == []


def test_migrate_adds_the_columns_and_backfills_tokens_on_an_old_table(tmp_path):
    """Regression for an existing production table that predates STEP75."""
    from scripts.init_db import migrate

    old = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with old.begin() as conn:
        conn.execute(text(
            "CREATE TABLE price_alerts (id INTEGER PRIMARY KEY, product_id INTEGER, email VARCHAR(255),"
            " target_price INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notified_at TIMESTAMP)"
        ))
        conn.execute(text("INSERT INTO price_alerts (product_id, email, target_price) VALUES (1, 'a@x.jp', 1), (1, 'b@x.jp', 1)"))

    migrate(old)

    columns = {c["name"] for c in inspect(old).get_columns("price_alerts")}
    assert {"unsubscribe_token", "consented_at"} <= columns
    with old.connect() as conn:
        rows = conn.execute(text("SELECT unsubscribe_token, consented_at FROM price_alerts")).all()
    assert len({r[0] for r in rows}) == 2 and all(r[0] for r in rows)
    assert all(r[1] is None for r in rows)  # old rows stay "no consent recorded"
