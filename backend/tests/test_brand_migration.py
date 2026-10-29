from app import brand_migration, brands, crud, schemas


def _product(db, name, brand, category="putter"):
    return crud.create_product(db, schemas.ProductCreate(name=name, brand=brand, category=category, initial_price=30000))


LAB_AS_PING = "L.A.B. ラブゴルフLINK.1 リンク.1 パター ゼロトルク ブレードタイプ ピンタイプ"
WOSS_AS_PING = "WOSS PRO-03 PRO-04 パター トライアングルスタビリティー ブレード型 ピン型 ウォズ"
NOBRAND_AS_PING = "レビュー120件超え パター マレット タイプ / ピン タイプ / 軟鉄鍛造"


def test_shape_words_are_not_the_ping_brand():
    assert brands.match_brand("マレット タイプ / ピン タイプ / 軟鉄鍛造") is None
    assert brands.match_brand("ホワイトホット パター ピン 型") is None
    # the real maker still matches, in every spelling
    assert brands.match_brand("ピン G440 ドライバー") == "PING"
    assert brands.match_brand("ピンゴルフ G440 K ドライバー") == "PING"
    assert brands.match_brand("PING G430 アイアン") == "PING"


def test_dry_run_changes_nothing(db_session):
    lab = _product(db_session, LAB_AS_PING, "PING")
    result = brand_migration.run_brand_migration(db_session, apply=False)
    assert (result.applied, result.rebranded) == (False, 1)
    assert any("PING -> L.A.B Golf" in line for line in result.plan_lines)
    db_session.refresh(lab)
    assert lab.brand == "PING"


def test_apply_fixes_only_misfiled_products_and_is_idempotent(db_session):
    lab = _product(db_session, LAB_AS_PING, "PING")
    woss = _product(db_session, WOSS_AS_PING, "PING")
    nobrand = _product(db_session, NOBRAND_AS_PING, "PING")
    real = _product(db_session, "ピンゴルフ G440 K ドライバー", "PING", category="driver")
    plain = _product(db_session, "G440 ドライバー", "PING", category="driver")  # manual entry, no brand in name

    result = brand_migration.run_brand_migration(db_session, apply=True)
    assert (result.rebranded, result.sent_to_review) == (1, 2)
    for p in (lab, woss, nobrand, real, plain):
        db_session.refresh(p)
    assert lab.brand == "L.A.B Golf"
    assert woss.pending_review and nobrand.pending_review
    assert woss.brand == "PING"  # nothing better to guess - left for the admin
    assert not real.pending_review and not plain.pending_review
    assert real.brand == plain.brand == "PING"

    again = brand_migration.run_brand_migration(db_session, apply=True)
    assert (again.rebranded, again.sent_to_review) == (0, 0)


def test_migration_endpoint_requires_admin(client):
    assert client.post("/api/admin/run-brand-migration?dry_run=true").status_code in (401, 403)


def test_migration_endpoint_dry_run_returns_the_plan(client, admin_headers, db_session):
    _product(db_session, LAB_AS_PING, "PING")
    body = client.post("/api/admin/run-brand-migration?dry_run=true", headers=admin_headers).json()
    assert body["applied"] is False
    assert body["rebranded"] == 1
    assert any("L.A.B Golf" in line for line in body["plan_lines"])
