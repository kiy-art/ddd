from app import crud, popularity, rakuten, schemas


class _FakeRankingItem:
    def __init__(self, rank, item_name):
        self.rank = rank
        self.item_name = item_name


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
    assert checked == len(popularity.CATEGORY_GENRE_IDS)
    assert ranked == 0

    logs = crud.list_error_logs(db_session)
    assert any("popularity" in log.source for log in logs)
