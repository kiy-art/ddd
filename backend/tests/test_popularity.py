from app import crud, popularity, rakuten, schemas


class _FakeRankingItem:
    def __init__(self, rank, item_name, price=None, image_url=None, shop_name=None):
        self.rank = rank
        self.item_name = item_name
        self.item_url = f"https://item.rakuten.co.jp/shop/{rank}/"
        self.price = price
        self.image_url = image_url
        self.shop_name = shop_name
        self.review_count = None
        self.review_average = None


def _fixed_ranking(items_by_genre):
    def fake_fetch_ranking(genre_id, hits=30, timeout=10.0):
        return items_by_genre.get(genre_id, [])

    return fake_fetch_ranking


def test_sync_sets_rank_for_a_matched_product(db_session, monkeypatch):
    product = crud.create_product(
        db_session,
        schemas.ProductCreate(
            name="G440 ドライバー", brand="PING", category="driver", model_number="G440", initial_price=68000
        ),
    )
    ranking = [
        _FakeRankingItem(1, "テーラーメイド Qi35 ドライバー"),
        _FakeRankingItem(2, "PING G440 ドライバー 10.5度 純正シャフト"),
    ]
    monkeypatch.setattr(
        rakuten, "fetch_ranking", _fixed_ranking({popularity.CATEGORY_GENRE_IDS["driver"]: ranking})
    )

    ranked, checked = popularity.sync_popularity_rankings(db_session)

    assert checked == len(popularity.CATEGORY_GENRE_IDS)
    assert ranked == 1
    db_session.refresh(product)
    assert product.popularity_rank == 2
    assert product.popularity_updated_at is not None


def test_sync_clears_rank_for_a_product_no_longer_in_the_ranking(db_session, monkeypatch):
    product = crud.create_product(
        db_session,
        schemas.ProductCreate(
            name="G440 ドライバー", brand="PING", category="driver", model_number="G440", initial_price=68000
        ),
    )
    product.popularity_rank = 3
    db_session.commit()

    monkeypatch.setattr(rakuten, "fetch_ranking", _fixed_ranking({}))  # empty ranking this run

    popularity.sync_popularity_rankings(db_session)

    db_session.refresh(product)
    assert product.popularity_rank is None


def test_sync_never_matches_without_a_model_number(db_session, monkeypatch):
    """Brand alone is too weak a signal - a listing can share a brand
    without being this exact product."""
    crud.create_product(
        db_session,
        schemas.ProductCreate(name="謎のPINGクラブ", brand="PING", category="driver", initial_price=50000),
    )
    ranking = [_FakeRankingItem(1, "PING 謎のPINGクラブ 特価セール")]
    monkeypatch.setattr(
        rakuten, "fetch_ranking", _fixed_ranking({popularity.CATEGORY_GENRE_IDS["driver"]: ranking})
    )

    ranked, _ = popularity.sync_popularity_rankings(db_session)
    assert ranked == 0


def test_sync_does_not_match_a_different_brand(db_session, monkeypatch):
    crud.create_product(
        db_session,
        schemas.ProductCreate(
            name="G440 ドライバー", brand="PING", category="driver", model_number="G440", initial_price=68000
        ),
    )
    # Same model-looking string but a Callaway listing - must not match a PING product.
    ranking = [_FakeRankingItem(1, "キャロウェイ G440風 ドライバー")]
    monkeypatch.setattr(
        rakuten, "fetch_ranking", _fixed_ranking({popularity.CATEGORY_GENRE_IDS["driver"]: ranking})
    )

    ranked, _ = popularity.sync_popularity_rankings(db_session)
    assert ranked == 0


def test_sync_logs_and_continues_on_a_failing_category(db_session, monkeypatch):
    def fake_fetch_ranking(genre_id, hits=30, timeout=10.0):
        if genre_id == popularity.CATEGORY_GENRE_IDS["driver"]:
            raise RuntimeError("boom")
        return []

    monkeypatch.setattr(rakuten, "fetch_ranking", fake_fetch_ranking)

    ranked, checked = popularity.sync_popularity_rankings(db_session)
    # Only categories actually fetched count - the failing one doesn't.
    assert checked == len(popularity.CATEGORY_GENRE_IDS) - 1
    assert ranked == 0

    logs = crud.list_error_logs(db_session)
    assert any("popularity" in log.source for log in logs)


def test_sync_reports_plainly_when_no_category_could_be_fetched(db_session, monkeypatch):
    def fake_fetch_ranking(genre_id, hits=30, timeout=10.0):
        raise RuntimeError("Rakuten Ranking API 403: accessKey required")

    monkeypatch.setattr(rakuten, "fetch_ranking", fake_fetch_ranking)
    monkeypatch.setattr(popularity.time, "sleep", lambda s: None)

    ranked, checked = popularity.sync_popularity_rankings(db_session)
    assert (ranked, checked) == (0, 0)
    messages = [log.message for log in crud.list_error_logs(db_session)]
    assert any("1カテゴリも取得できませんでした" in m for m in messages)



# --- STEP59: Rakuten's own ranking list, stored and served -----------------------


def test_sync_stores_the_whole_ranking_and_links_catalog_matches(db_session, monkeypatch, client):
    product = crud.create_product(
        db_session,
        schemas.ProductCreate(
            name="G440 ドライバー", brand="PING", category="driver", model_number="G440", initial_price=68000
        ),
    )
    ranking = [
        _FakeRankingItem(1, "【送料無料】テーラーメイド Qi35 ドライバー", price=79800, shop_name="ゴルフ5"),
        _FakeRankingItem(2, "PING G440 ドライバー 10.5度 純正シャフト", price=68200),
        _FakeRankingItem(3, "謎ブランド ドライバー", price=9800),
    ]
    monkeypatch.setattr(
        rakuten, "fetch_ranking", _fixed_ranking({popularity.CATEGORY_GENRE_IDS["driver"]: ranking})
    )
    popularity.sync_popularity_rankings(db_session)

    body = client.get("/api/popular/rakuten-ranking?limit=10").json()
    driver = next(g for g in body if g["category"] == "driver")
    assert [e["rank"] for e in driver["entries"]] == [1, 2, 3]  # every listing, not just catalog matches
    first = driver["entries"][0]
    assert first["name"] == "テーラーメイド Qi35 ドライバー"  # promo noise stripped
    assert (first["price"], first["shop_name"], first["product_slug"]) == (79800, "ゴルフ5", None)
    assert driver["entries"][1]["product_slug"] == product.slug

    # a re-sync replaces the snapshot instead of piling up rows
    popularity.sync_popularity_rankings(db_session)
    body = client.get("/api/popular/rakuten-ranking").json()
    assert len(next(g for g in body if g["category"] == "driver")["entries"]) == 3


def test_a_stale_ranking_snapshot_is_not_served(db_session, monkeypatch, client):
    import datetime

    from app import models

    ranking = [_FakeRankingItem(1, "テーラーメイド Qi35 ドライバー")]
    monkeypatch.setattr(
        rakuten, "fetch_ranking", _fixed_ranking({popularity.CATEGORY_GENRE_IDS["driver"]: ranking})
    )
    popularity.sync_popularity_rankings(db_session)
    for row in db_session.query(models.RakutenRankingEntry):
        row.fetched_at = datetime.datetime.utcnow() - datetime.timedelta(days=popularity.RANKING_MAX_AGE_DAYS + 1)
    db_session.commit()
    assert client.get("/api/popular/rakuten-ranking").json() == []


def test_ranking_parser_keeps_price_image_shop_and_reviews(monkeypatch):
    from app.config import get_settings

    class _Resp:
        is_error = False
        status_code = 200

        def json(self):
            return {
                "Items": [
                    {
                        "Item": {
                            "rank": 1,
                            "itemName": "Qi35 ドライバー",
                            "itemUrl": "https://item.rakuten.co.jp/x/1/",
                            "itemPrice": "79800",
                            "mediumImageUrls": [{"imageUrl": "https://thumbnail.image.rakuten.co.jp/a.jpg?_ex=128x128"}],
                            "shopName": "ゴルフ5",
                            "reviewCount": 12,
                            "reviewAverage": "4.5",
                        }
                    }
                ]
            }

    monkeypatch.setenv("RAKUTEN_APP_ID", "id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "key")
    get_settings.cache_clear()
    try:
        monkeypatch.setattr(rakuten.http_retry, "get_with_retry", lambda *a, **k: _Resp())
        item = rakuten.fetch_ranking(201706)[0]
        assert (item.price, item.shop_name, item.review_count, item.review_average) == (79800, "ゴルフ5", 12, 4.5)
        assert item.image_url == "https://thumbnail.image.rakuten.co.jp/a.jpg?_ex=300x300"
    finally:
        get_settings.cache_clear()
