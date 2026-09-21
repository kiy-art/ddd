from app import crud, discovery, rakuten, schemas


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
    ever become a (pending) product."""
    items = [
        _FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/"),
        _FakeItem("PING G440用 ヘッドカバー", 2500, "https://item.rakuten.co.jp/example/cover/"),
        _FakeItem("ゴルフ ドライバー ジャンク品", 500, "https://item.rakuten.co.jp/example/junk/"),
        _FakeItem("謎のゴルフクラブ", 15000, "https://item.rakuten.co.jp/example/unbranded/"),
    ]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"]: items})
    )

    discovered, considered = discovery.discover_new_products(db_session)

    assert considered == 4
    assert discovered == 1

    product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
    assert product is not None
    assert product.pending_review is True
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
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"]: items})
    )

    discovered, _ = discovery.discover_new_products(db_session)
    assert discovered == 0


def test_discover_new_products_respects_the_per_category_cap(db_session, monkeypatch):
    items = [
        _FakeItem(f"PING G{440 + i} ドライバー", 60000 + i, f"https://item.rakuten.co.jp/example/g{i}/")
        for i in range(discovery.MAX_NEW_PER_CATEGORY + 3)
    ]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"]: items})
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
            rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"]: items})
        )

        discovery.discover_new_products(db_session)

        product = crud.find_product_by_identity(db_session, "PING G440 ドライバー", "PING", None)
        assert product.affiliate_url.startswith(
            "https://hb.afl.rakuten.co.jp/ichiba/38e4bda3.3d4c8086.38e4bda4.cefadc6a/?pc="
        )
    finally:
        get_settings.cache_clear()


def test_discovered_products_are_hidden_from_public_listing(db_session, monkeypatch):
    items = [_FakeItem("PING G440 ドライバー", 68000, "https://item.rakuten.co.jp/example/g440/")]
    monkeypatch.setattr(
        rakuten, "search_items", _fixed_results({discovery.CATEGORY_SEARCH_KEYWORDS["driver"]: items})
    )
    discovery.discover_new_products(db_session)

    published = crud.list_products(db_session, published_only=True)
    assert published == []

    pending = crud.list_pending_products(db_session)
    assert len(pending) == 1
    assert pending[0].name == "PING G440 ドライバー"
