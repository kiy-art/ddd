import datetime

from sqlalchemy import select

from app import categorizer, category_migration, crud, models, schemas


def _product(db, name, category, brand="LITE"):
    return crud.create_product(db, schemas.ProductCreate(name=name, brand=brand, category=category, initial_price=1500))


# --- classifier ------------------------------------------------------------------


def test_accessories_filed_as_clubs_or_balls_are_recognised():
    assert categorizer.corrected_category("ボールマーカー 3個セット", "ball") == "other"
    assert categorizer.corrected_category("ピンフラッグ 練習用", "putter") == "other"
    assert categorizer.corrected_category("パター練習用カップ", "putter") == "other"
    assert categorizer.corrected_category("パターマット 3m", "putter") == "other"
    assert categorizer.corrected_category("ウェザーソフ グローブ", "ball") == "glove"
    assert categorizer.corrected_category("ピンシーカー プロX3 レーザー距離計", "driver") == "rangefinder"
    assert categorizer.corrected_category("グローブ 2枚セット", "other") == "glove"


def test_real_clubs_and_balls_with_bundled_extras_stay_put():
    assert categorizer.corrected_category("Qi35 ドライバー グローブプレゼント", "driver") is None
    assert categorizer.corrected_category("Pro V1 ゴルフボール 1ダース マーカー付き", "ball") is None
    assert categorizer.corrected_category("ホワイトホット パター ピン型", "putter") is None
    assert categorizer.corrected_category("G440 ドライバー ヘッドカバー付き", "driver") is None
    assert categorizer.corrected_category("グローブライド オノフ ドライバー", "driver") is None
    # the title cleaner strips "ボール" from stored ball names - a plain
    # model name has no opinion either way
    assert categorizer.corrected_category("Pro V1", "ball") is None
    # never moves anything out of glove/rangefinder
    assert categorizer.corrected_category("ボールマーカー", "glove") is None


# --- migration ---------------------------------------------------------------------


def test_dry_run_changes_nothing(db_session):
    marker = _product(db_session, "ボールマーカー 3個セット", "ball")
    result = category_migration.run_category_migration(db_session, apply=False)
    assert (result.applied, result.moved) == (False, 1)
    assert any("ボール -> その他" in line for line in result.plan_lines)
    db_session.refresh(marker)
    assert marker.category == "ball"


def test_apply_moves_only_misfiled_products_and_is_idempotent(db_session):
    marker = _product(db_session, "ボールマーカー 3個セット", "ball")
    glove = _product(db_session, "ウェザーソフ グローブ", "ball", brand="FootJoy")
    ball = _product(db_session, "Pro V1 ゴルフボール 1ダース", "ball", brand="Titleist")
    marker.popularity_rank = 4
    marker.popularity_updated_at = datetime.datetime.utcnow()
    db_session.commit()

    result = category_migration.run_category_migration(db_session, apply=True)
    assert result.moved == 2
    assert result.moved_by_category == {"other": 1, "glove": 1}
    for p in (marker, glove, ball):
        db_session.refresh(p)
    assert (marker.category, glove.category, ball.category) == ("other", "glove", "ball")
    assert marker.popularity_rank is None  # old category's rank cleared

    again = category_migration.run_category_migration(db_session, apply=True)
    assert again.moved == 0


def test_moved_products_show_on_their_new_category_page(client, db_session):
    glove = _product(db_session, "ウェザーソフ グローブ", "ball", brand="FootJoy")
    crud.add_price(db_session, glove, 1480)
    for h in db_session.execute(select(models.PriceHistory).where(models.PriceHistory.product_id == glove.id)).scalars():
        h.recorded_at = datetime.datetime.utcnow() - datetime.timedelta(days=2)
    db_session.commit()
    crud.add_price(db_session, glove, 1450)
    from app import pipeline

    pipeline.sync_product_analysis(db_session, glove)
    category_migration.run_category_migration(db_session, apply=True)
    names = [p["name"] for p in client.get("/api/categories/glove").json()]
    assert "ウェザーソフ グローブ" in names


def test_migration_endpoint_requires_admin(client):
    assert client.post("/api/admin/run-category-migration?dry_run=true").status_code in (401, 403)


def test_migration_endpoint_dry_run_returns_the_plan(client, admin_headers, db_session):
    _product(db_session, "ピンフラッグ 練習用", "putter")
    body = client.post("/api/admin/run-category-migration?dry_run=true", headers=admin_headers).json()
    assert body["applied"] is False and body["moved"] == 1
    assert any("パター -> その他" in line for line in body["plan_lines"])
    assert db_session.execute(select(models.Product.category)).scalar() == "putter"
