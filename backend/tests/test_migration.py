"""Regression test for a real production incident: scripts/init_db.py added
`buy_signal_score`/`history_span_days` via a bare ALTER TABLE ADD COLUMN,
which leaves every pre-existing row's new column NULL. `history_span_days`
is non-nullable in schemas.ProductOut, so every /api/products response
started failing Pydantic validation with a 500
("商品情報の取得に失敗しました") until a backfill was added. This test
builds a SQLite table matching the schema from *before* that migration,
with an existing row (exactly the production scenario), runs the real
migrate() function against it, and asserts the result actually
deserializes through ProductOut - not just that the column exists.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import crud, schemas  # noqa: E402
from app.database import Base  # noqa: E402
from scripts.init_db import fix_known_bad_products, migrate  # noqa: E402


@pytest.fixture
def pre_migration_engine(tmp_path):
    """A fresh SQLite DB with the products table as it looked *before*
    buy_signal_score/history_span_days/pending_review existed, containing
    one row created under that old schema."""
    db_path = tmp_path / "pre_migration.db"
    engine = create_engine(f"sqlite:///{db_path}")

    table = Base.metadata.tables["products"]
    dialect = engine.dialect
    columns_sql = []
    for col in table.columns:
        if col.name in ("buy_signal_score", "history_span_days", "pending_review"):
            continue
        coltype = col.type.compile(dialect=dialect)
        pk = " PRIMARY KEY" if col.primary_key else ""
        nullable = "" if col.nullable else " NOT NULL"
        columns_sql.append(f'"{col.name}" {coltype}{pk}{nullable}')

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE products (" + ", ".join(columns_sql) + ")"))
        conn.execute(
            text(
                "INSERT INTO products (slug, name, brand, category, buy_score, current_price, "
                "created_at, updated_at) VALUES "
                "('old-product', 'Old Product', 'Brand', 'iron', 'strong_buy', 50000, "
                "datetime('now'), datetime('now'))"
            )
        )

    return engine


def test_migrate_backfills_history_span_days_for_preexisting_rows(pre_migration_engine):
    migrate(pre_migration_engine)

    with pre_migration_engine.begin() as conn:
        row = conn.execute(
            text("SELECT history_span_days, buy_signal_score FROM products WHERE slug = 'old-product'")
        ).fetchone()

    assert row.history_span_days == 0  # backfilled, not NULL
    assert row.buy_signal_score is None  # nullable in the schema, NULL is fine here


def test_migrate_result_is_a_valid_product_out(pre_migration_engine):
    """The actual regression: does the migrated row satisfy the API schema
    that broke in production?"""
    migrate(pre_migration_engine)

    with pre_migration_engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM products WHERE slug = 'old-product'")).mappings().one()

    # Raises a pydantic ValidationError (the exact failure mode that
    # produced the 500) if history_span_days is still None/missing.
    product = schemas.ProductOut.model_validate(dict(row))
    assert product.history_span_days == 0


def test_migrate_is_idempotent(pre_migration_engine):
    migrate(pre_migration_engine)
    migrate(pre_migration_engine)  # must not raise (duplicate column, etc.)

    with pre_migration_engine.begin() as conn:
        row = conn.execute(
            text("SELECT history_span_days FROM products WHERE slug = 'old-product'")
        ).fetchone()
    assert row.history_span_days == 0


@pytest.fixture
def orm_session(tmp_path):
    """A fresh DB on the current full schema, with a real ORM session —
    for fix_known_bad_products, which uses crud functions rather than raw
    SQL."""
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'orm.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_fix_known_bad_products_restores_the_real_elyte_max_fast_price(orm_session):
    """Regression test for a real production incident: ELYTE MAX FAST
    driver's first-ever Rakuten fetch (no reference price to sanity-check
    against) matched a ¥2,180 accessory listing instead of the driver
    itself. This restores the real price from data/real_products_batch1.csv
    and clears the accessory photo/link."""
    product = crud.create_product(
        orm_session,
        schemas.ProductCreate(
            name="ELYTE MAX FAST ドライバー", brand="Callaway", category="driver", model_number="ELYTE MAX FAST"
        ),
    )
    crud.add_price(orm_session, product, 2180)
    product.image_url = "https://thumbnail.image.rakuten.co.jp/example/weight-cap.jpg"
    product.affiliate_url = "https://item.rakuten.co.jp/example/weight-cap/"
    orm_session.commit()

    fix_known_bad_products(orm_session)

    orm_session.refresh(product)
    assert product.current_price == 107800
    assert product.image_url is None
    assert product.affiliate_url is None
    assert [h.price for h in crud.get_price_history(orm_session, product.id)] == [107800]


def test_fix_known_bad_products_is_idempotent_and_leaves_healthy_data_alone(orm_session):
    product = crud.create_product(
        orm_session,
        schemas.ProductCreate(
            name="ELYTE MAX FAST ドライバー", brand="Callaway", category="driver", model_number="ELYTE MAX FAST"
        ),
    )
    crud.add_price(orm_session, product, 2180)

    fix_known_bad_products(orm_session)
    fix_known_bad_products(orm_session)  # must not re-trigger once fixed

    orm_session.refresh(product)
    assert product.current_price == 107800
    assert [h.price for h in crud.get_price_history(orm_session, product.id)] == [107800]


def test_fix_known_bad_products_ignores_products_that_were_never_broken(orm_session):
    healthy = crud.create_product(
        orm_session,
        schemas.ProductCreate(
            name="ELYTE MAX FAST ドライバー",
            brand="Callaway",
            category="driver",
            model_number="ELYTE MAX FAST",
            initial_price=95000,
        ),
    )

    fix_known_bad_products(orm_session)

    orm_session.refresh(healthy)
    assert healthy.current_price == 95000
