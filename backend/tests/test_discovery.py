import pytest
from sqlalchemy import select

from app import crud, discovery, models, rakuten, schemas


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    # discover_new_products sleeps RAKUTEN_REQUEST_INTERVAL_SECONDS between
    # real Rakuten requests to stay under its rate limit - with more
    # keywords per category (STEP12) that adds up across this file's many
    # tests, none of which make a real request worth pacing.
    monkeypatch.setattr(discovery.time, "sleep", lambda *_args: None)


class _FakeItem:
    def __init__(self, item_name, price, item_url, image_url=None):
        self.item_name = item_name
        self.price = price
        self.item_url = item_url
        self.image_url = image_url


def _fixed_results(items_by_keyword):
    def fake_search_items(keyword, hits=10, timeout=10.0):
        return items_by_keyword.get(keyword, [])

    return fake_search_items


def test_discover_new_products_filters_out_everything_but_a_valid_candidate(db_session, monkeypatch):
    """A single search can return a real product, an accessory, a too-cheap
    junk listing, and an unbranded listing — only the real product should
    ever become a product at all (pending or otherwise)."""
    items = [
        _FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/"),
        _FakeItem("PING G440用 ヘッドカバー", 2500, "https://item.rakuten.co.jp/example/cover/"),
        _FakeItem("ゴルフ ドライバー ジャンク品", 500, "https://item.rakuten.co.jp/example/junk/"),
        _FakeItem("謎のゴルフクラブ", 15000, "https://item.rakuten.co.jp/example/unbranded/"),
    ]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )

    discovered, considered = discovery.discover_new_products(db_session)

    assert considered == 4
    assert discovered == 1

    product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
    assert product is not None
    # Clean name, no NG keyword, priced well above the club auto-publish
    # floor - safe to publish immediately (see _is_safe_to_auto_publish).
    assert product.pending_review is False
    assert product.current_price == 68000
    assert product.category == "driver"


def test_discover_new_products_skips_items_already_in_the_catalog(db_session, monkeypatch):
    crud.create_product(
        db_session,
        schemas.ProductCreate(
            name="PING G440 ドライバー",
            brand="PING",
            category="driver",
            affiliate_url="https://item.rakuten.co.jp/example/g440/",
            initial_price=68000,
        ),
    )
    items = [_FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )

    discovered, _ = discovery.discover_new_products(db_session)
    assert discovered == 0


def test_discover_new_products_respects_the_per_category_cap(db_session, monkeypatch):
    items = [
        _FakeItem(f"PING G{440 + i} ドライバー", 60000 + i, f"https://item.rakuten.co.jp/example/g{i}/")
        for i in range(discovery.MAX_NEW_PER_CATEGORY + 3)
    ]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )

    discovered, considered = discovery.discover_new_products(db_session)
    assert discovered == discovery.MAX_NEW_PER_CATEGORY
    assert considered == discovery.MAX_NEW_PER_CATEGORY  # loop breaks once the cap is hit


def test_discover_new_products_wraps_affiliate_url_when_affiliate_id_configured(db_session, monkeypatch):
    monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "38e4bda3.3d4c8086.38e4bda4.cefadc6a")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        items = [_FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/")]
        monkeypatch.setattr(
            rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
        )

        discovery.discover_new_products(db_session)

        product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
        assert product.affiliate_url.startswith(
            "https://hb.afl.rakuten.co.jp/ichiba/38e4bda3.3d4c8086.38e4bda4.cefadc6a/?pc="
        )
    finally:
        get_settings.cache_clear()


def test_discovered_products_needing_review_are_hidden_from_public_listing(db_session, monkeypatch):
    # Priced below the club auto-publish floor (AUTO_PUBLISH_MIN_PRICE_CLUB)
    # - still a valid candidate (above MIN_DISCOVERY_PRICE), just not safe
    # to skip human review.
    items = [_FakeItem("PING G440 ドライバー", 8000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )
    discovery.discover_new_products(db_session)

    published = crud.list_products(db_session, published_only=True)
    assert published == []

    pending = crud.list_pending_products(db_session)
    assert len(pending) == 1
    assert pending[0].name == "PING G440 ドライバー"


def test_auto_publish_skips_review_queue_for_a_safe_candidate(db_session, monkeypatch):
    items = [_FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )
    discovery.discover_new_products(db_session)

    assert crud.list_pending_products(db_session) == []
    product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
    assert product.pending_review is False


def test_auto_publish_respects_the_lower_ball_price_floor(db_session, monkeypatch):
    # Below the club floor (10,000) but above the ball floor (3,000) and
    # above MIN_DISCOVERY_PRICE - a dozen balls at this price is plausible.
    items = [_FakeItem("Titleist Pro V1 ゴルフボール 1ダース", 5500, "https://item.rakuten.co.jp/example/provx1/")]
    ball_keyword = discovery.CATEGORY_SEARCH_KEYWORDS["ball"][1]  # the Pro V1-specific keyword
    monkeypatch.setattr(rakuten, "search_items", _fixed_results({ball_keyword: items}))

    discovery.discover_new_products(db_session)

    product = crud.find_product_by_identity(db_session, "Titleist Pro V1", "Titleist", None)
    assert product is not None
    assert product.pending_review is False


@pytest.mark.parametrize(
    # Both of these are still accepted as candidates at all (they don't
    # match _looks_like_accessory's own, earlier reject list) - they only
    # get held for review by the auto-publish NG list specifically.
    "item_name",
    ["PING G440 中古 ドライバー", "PING G440 レディース用 ドライバー"],
)
def test_auto_publish_ng_keywords_stay_pending_even_when_priced_high(db_session, monkeypatch, item_name):
    items = [_FakeItem(item_name, 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )
    discovery.discover_new_products(db_session)

    product = crud.find_product_by_identity(db_session, item_name, "PING", None)
    assert product is not None
    assert product.pending_review is True


@pytest.mark.parametrize("item_name", ["PING G440 ふるさと納税 ドライバー", "PING G440 ドライバー 訳あり"])
def test_discover_new_products_rejects_non_retail_listings_entirely(db_session, monkeypatch, item_name):
    """Unlike the auto-publish NG list above (still added, just pending),
    a furusato-nozei donation-reward listing or a damaged/defective
    clearance listing isn't a normal retail sale at all and must never
    become a product - pending or otherwise (STEP15)."""
    items = [_FakeItem(item_name, 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )
    discovered, considered = discovery.discover_new_products(db_session)

    assert considered == 1
    assert discovered == 0
    assert crud.list_pending_products(db_session) == []


def test_discover_new_products_stores_a_cleaned_title_not_the_raw_listing_title(db_session, monkeypatch):
    raw_title = "【送料無料】PING G440 ドライバー ポイント10倍!!"
    items = [_FakeItem(raw_title, 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"][0]: items})
    )
    discovery.discover_new_products(db_session)

    product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
    assert product is not None
    assert product.name == "PING G440 ドライバー"
    assert "送料無料" not in product.name
    assert "ポイント" not in product.name


def test_discover_new_products_dedups_by_cleaned_title_across_differently_noisy_raw_titles(db_session, monkeypatch):
    """Two listings of the same real ball, found under two different ball
    keywords (see CATEGORY_SEARCH_KEYWORDS["ball"], STEP12), whose raw shop
    titles differ only in promotional noise - must collapse into one
    product, not register as two (STEP15)."""
    ball_keywords = discovery.CATEGORY_SEARCH_KEYWORDS["ball"]
    item_a = _FakeItem(
        "【送料無料】Titleist Pro V1 ゴルフボール 1ダース", 5500, "https://item.rakuten.co.jp/example/provx-a/"
    )
    item_b = _FakeItem(
        "Titleist Pro V1 ゴルフボール 1ダース ポイント10倍!!", 5400, "https://item.rakuten.co.jp/example/provx-b/"
    )
    monkeypatch.setattr(
        rakuten,
        "search_items",
        _fixed_results({ball_keywords[0]: [item_a], ball_keywords[1]: [item_b]}),
    )

    discovered, _ = discovery.discover_new_products(db_session)

    assert discovered == 1
    all_products = list(db_session.execute(select(models.Product)).scalars().all())
    matching = [p for p in all_products if p.name == "Titleist Pro V1"]
    assert len(matching) == 1
