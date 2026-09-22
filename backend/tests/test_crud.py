import datetime

from app import crud, schemas


def _days_ago(n):
    return datetime.datetime.utcnow() - datetime.timedelta(days=n)


def _make_product(db_session, name, brand, msrp=None):
    return crud.create_product(
        db_session,
        schemas.ProductCreate(
            name=name,
            brand=brand,
            category="driver",
            model_number=name,
            msrp=msrp,
        ),
    )


def _seed_history(db_session, product, prices_oldest_first):
    for i, price in enumerate(prices_oldest_first):
        days_ago = (len(prices_oldest_first) - 1 - i) * 5
        crud.add_price(db_session, product, price, recorded_at=_days_ago(days_ago))


def test_brand_price_stats_with_no_products(db_session):
    stats = crud.get_brand_price_stats(db_session, "Nonexistent Brand")
    assert stats.tracked_count == 0
    assert stats.reliable_count == 0
    assert stats.average_change_percent is None
    assert stats.average_msrp_discount_percent is None
    assert stats.biggest_decline is None


def test_brand_price_stats_counts_declining_and_rising(db_session):
    declining = _make_product(db_session, "Declining Driver", "Acme")
    _seed_history(db_session, declining, [10000, 9500, 9000])  # oldest -> newest, going down

    rising = _make_product(db_session, "Rising Driver", "Acme")
    _seed_history(db_session, rising, [9000, 9500, 10000])  # going up

    stats = crud.get_brand_price_stats(db_session, "Acme")
    assert stats.tracked_count == 2
    assert stats.reliable_count == 2
    assert stats.declining_count == 1
    assert stats.rising_count == 1
    assert stats.average_change_percent is not None
    assert stats.biggest_decline is not None
    assert stats.biggest_decline.product_slug == declining.slug


def test_brand_price_stats_excludes_unpublished_thin_history(db_session):
    # Only one price point ever recorded - insufficient_data, so this
    # product isn't "published" anywhere else on the site either (see
    # list_products' published_only filter) and shouldn't inflate a
    # brand's tracked/reliable counts.
    thin = _make_product(db_session, "Thin Driver", "Acme")
    crud.add_price(db_session, thin, 10000)

    stats = crud.get_brand_price_stats(db_session, "Acme")
    assert stats.tracked_count == 0
    assert stats.reliable_count == 0
    assert stats.average_change_percent is None


def test_brand_price_stats_msrp_discount_uses_all_tracked_products(db_session):
    # MSRP discount doesn't require the fuller "reliable trend" history bar
    # - it's a single fixed-reference comparison, same as ProductCard's
    # msrpPct - but the product still needs to be published (2+ price
    # points) to count at all, same as everywhere else on the site.
    product = _make_product(db_session, "MSRP Driver", "Acme", msrp=10000)
    crud.add_price(db_session, product, 8500, recorded_at=_days_ago(1))
    crud.add_price(db_session, product, 8000)

    stats = crud.get_brand_price_stats(db_session, "Acme")
    assert stats.average_msrp_discount_percent == -20.0
    assert stats.reliable_count == 0  # span too short to count as a reliable trend


def test_brand_price_stats_scoped_to_one_brand(db_session):
    a = _make_product(db_session, "Brand A Driver", "Acme")
    _seed_history(db_session, a, [10000, 9500, 9000])
    b = _make_product(db_session, "Brand B Driver", "Beta")
    _seed_history(db_session, b, [10000, 9500, 9000])

    stats = crud.get_brand_price_stats(db_session, "Acme")
    assert stats.tracked_count == 1
