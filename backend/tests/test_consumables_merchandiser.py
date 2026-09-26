import datetime

import pytest

from app import consumables_catalog, consumables_merchandiser as cm, crud, models, rakuten, schemas

NOW = datetime.datetime(2026, 6, 15, 3, 0)  # 12:00 JST, rainy season
DAY = datetime.date(2026, 6, 15)


def _days_ago(n):
    return NOW - datetime.timedelta(days=n)


def _item(db, slug, kind="glove", price=2000, msrp=None, history=(), seasons="rainy", rakuten_url="https://item.rakuten.co.jp/x/", fresh=True):
    item = models.ConsumableItem(
        slug=slug, kind=kind, brand="FootJoy", name=f"{slug} name", search_keyword=slug,
        match_tokens="footjoy", seasons=seasons, msrp=msrp, current_price=price, rakuten_url=rakuten_url,
        price_updated_at=NOW if fresh else _days_ago(30), active=True,
    )
    db.add(item)
    db.commit()
    for p, days in history:
        db.add(models.ConsumablePriceHistory(item_id=item.id, price=p, recorded_at=_days_ago(days)))
    db.commit()
    return item


# --- reference price: only real bases, always labeled -------------------------


def test_reference_prefers_a_real_msrp():
    ref = cm.reference_price(2000, 2500, [], NOW)
    assert (ref.price, ref.basis, ref.label) == (2500, "msrp", "メーカー希望小売価格")


def test_reference_falls_back_to_the_recorded_30_day_median():
    history = [(2400, _days_ago(d)) for d in (20, 15, 12, 9, 2)]
    ref = cm.reference_price(2000, None, history, NOW)
    assert (ref.price, ref.basis, ref.label) == (2400, "median30", "直近30日の中央値")


@pytest.mark.parametrize(
    "history",
    [
        [(2400, _days_ago(d)) for d in (3, 2, 1)],  # too few records
        [(2400, _days_ago(d)) for d in (5, 4, 3, 2, 1)],  # span < 7 days
        [(2400, _days_ago(d)) for d in (60, 55, 50, 45, 40)],  # outside the 30-day window
    ],
)
def test_no_reference_without_enough_real_history(history):
    assert cm.reference_price(2000, None, history, NOW) is None


def test_no_reference_when_the_price_isnt_actually_lower():
    assert cm.reference_price(2600, 2500, [], NOW) is None


# --- discount math ---------------------------------------------------------------


def test_discount_is_floored_never_rounded_up():
    # 2500 -> 2001 is 19.96% off: shown as 19%, never "20% OFF".
    pct, savings = cm._discount(2001, cm.Reference(2500, "msrp", "メーカー希望小売価格"))
    assert (pct, savings) == (19, 499)


def test_tiny_discounts_get_no_badge():
    assert cm._discount(2450, cm.Reference(2500, "msrp", "x")) == (None, None)


# --- seasons & sale events ---------------------------------------------------------


@pytest.mark.parametrize(
    "day, season",
    [
        (datetime.date(2026, 1, 10), "winter"),
        (datetime.date(2026, 3, 1), "spring"),
        (datetime.date(2026, 6, 1), "rainy"),
        (datetime.date(2026, 7, 16), "summer"),
        (datetime.date(2026, 9, 11), "autumn"),
        (datetime.date(2026, 12, 1), "winter"),
    ],
)
def test_season_boundaries(day, season):
    assert cm.season_for(day) == season


def test_sale_events_come_only_from_owner_entered_dates():
    raw = '[{"name": "楽天スーパーSALE", "shop": "rakuten", "start": "2026-06-04", "end": "2026-06-11"}]'
    assert [e.name for e in cm.active_sale_events(datetime.date(2026, 6, 5), raw)] == ["楽天スーパーSALE"]
    assert cm.active_sale_events(datetime.date(2026, 6, 15), raw) == []  # after it ended
    assert cm.active_sale_events(DAY, "") == []  # nothing entered -> no claim
    assert cm.active_sale_events(DAY, "not json") == []
    assert cm.active_sale_events(DAY, '[{"name": "x"}]') == []  # missing dates -> ignored


# --- selection -------------------------------------------------------------------------


def test_select_picks_needs_at_least_three_real_fresh_items(db_session):
    _item(db_session, "a")
    _item(db_session, "b", kind="tee")
    _item(db_session, "stale", kind="care", fresh=False)  # old price: not "now"
    assert cm.select_picks(db_session, today=DAY, now=NOW)[2] == []


def test_select_picks_ranks_real_discounts_and_badges_them_with_their_basis(db_session):
    _item(db_session, "big-discount", price=1500, msrp=2500)
    _item(db_session, "no-reference", kind="tee", price=500, seasons="autumn")
    _item(db_session, "median-discount", kind="care", price=800,
          history=[(1000, d) for d in (20, 15, 12, 9, 2)])

    season, events, picks = cm.select_picks(db_session, today=DAY, now=NOW)
    assert season == "rainy" and events == []
    by_key = {p.name: p for p in picks}

    top = picks[0]
    assert top.name == "big-discount name"
    assert top.discount_badge == "🔥 40% OFF"
    assert top.savings_text == "メーカー希望小売価格より1,000円安い"

    median = by_key["median-discount name"]
    assert median.savings_text == "直近30日の中央値より200円安い"

    plain = by_key["no-reference name"]
    assert plain.discount_badge is None and plain.savings_text is None  # no invented 通常価格
    assert "現在価格" in plain.micro_copy


def test_select_picks_keeps_variety_and_caps_at_six(db_session):
    for i in range(5):
        _item(db_session, f"glove-{i}", price=1500, msrp=2500)
    for i in range(3):
        _item(db_session, f"tee-{i}", kind="tee", price=500)
    picks = cm.select_picks(db_session, today=DAY, now=NOW)[2]
    assert len(picks) == 6
    # variety first: at most 2 of each kind before filling by score
    first = [p.kind for p in picks[:4]]
    assert first.count("glove") == 2 and first.count("tee") == 2


def test_select_picks_includes_catalog_balls_with_their_real_msrp(db_session):
    ball = crud.create_product(
        db_session, schemas.ProductCreate(name="Pro V1 1ダース", brand="Titleist", category="ball", initial_price=6000)
    )
    ball.msrp = 7920
    db_session.commit()
    for h in ball.price_history:
        h.recorded_at = NOW - datetime.timedelta(hours=1)
    db_session.commit()
    _item(db_session, "g1")
    _item(db_session, "t1", kind="tee")

    picks = cm.select_picks(db_session, today=DAY, now=NOW)[2]
    ball_pick = next(p for p in picks if p.kind == "ball")
    assert ball_pick.product_slug == ball.slug
    assert ball_pick.discount_badge == "🔥 24% OFF"  # (7920-6000)/7920 = 24.2%

    # the product page excludes its own product from the corner
    picks = cm.select_picks(db_session, today=DAY, now=NOW, exclude_product_id=ball.id)[2]
    assert picks == []  # only 2 left -> corner hidden rather than half-empty


def test_seasonal_items_get_situational_tags_not_superlatives(db_session):
    _item(db_session, "rain", seasons="rainy")
    _item(db_session, "t", kind="tee", seasons="autumn")
    _item(db_session, "c", kind="care", seasons="rainy")
    picks = cm.select_picks(db_session, today=DAY, now=NOW)[2]
    tags = {p.name: p.ai_tag for p in picks}
    assert tags["rain name"] == "梅雨どきの替えグローブに"
    assert tags["c name"] == "雨上がりのお手入れに"
    for p in picks:
        assert "最強" not in p.ai_tag + p.micro_copy and "必ず" not in p.ai_tag + p.micro_copy


def test_an_owner_entered_rakuten_event_tags_rakuten_items(db_session, monkeypatch):
    monkeypatch.setattr(
        cm, "active_sale_events", lambda day, raw=None: [cm.SaleEvent("楽天スーパーSALE", "rakuten", DAY, DAY)]
    )
    _item(db_session, "a")
    _item(db_session, "b", kind="tee")
    _item(db_session, "c", kind="care", rakuten_url=None)
    season, events, picks = cm.select_picks(db_session, today=DAY, now=NOW)
    tags = {p.name: p.ai_tag for p in picks}
    assert tags["a name"] == "楽天スーパーSALE期間中"
    assert tags["c name"] != "楽天スーパーSALE期間中"  # no Rakuten link -> no event claim


# --- daily refresh: only listings that are really this item ------------------------------


class _Listing:
    def __init__(self, name, price=2200):
        self.item_name = name
        self.price = price
        self.item_url = "https://item.rakuten.co.jp/shop/fj/"
        self.image_url = "http://thumbnail.image.rakuten.co.jp/@0_mall/shop/fj.jpg"


def test_listing_token_matching():
    tokens = "フットジョイ|footjoy,レイングリップ|raingrip"
    assert cm.listing_matches_tokens("FootJoy RainGrip レイン グローブ 両手", tokens)
    assert cm.listing_matches_tokens("フットジョイ レイングリップ グローブ", tokens)
    assert not cm.listing_matches_tokens("フットジョイ ウェザーソフ グローブ", tokens)


def test_refresh_records_price_only_for_a_matching_listing(db_session, monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    names = {
        "フットジョイ ウェザーソフ グローブ": "FootJoy ウェザーソフ グローブ 左手用",
        "フットジョイ レイングリップ グローブ": "FootJoy ウェザーソフ グローブ",  # wrong item
    }
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda kw: _Listing(names[kw]) if kw in names else None)

    updated, skipped = cm.refresh_consumable_prices(db_session)
    assert updated == 1
    assert skipped == len(consumables_catalog.CONSUMABLES) - 1

    by_slug = {i.slug: i for i in db_session.query(models.ConsumableItem).all()}
    weathersof = by_slug["footjoy-weathersof-glove"]
    assert weathersof.current_price == 2200
    assert weathersof.image_url == "https://thumbnail.image.rakuten.co.jp/@0_mall/shop/fj.jpg"  # normalized
    assert len(weathersof.price_history) == 1
    assert by_slug["footjoy-raingrip-glove"].current_price is None  # mismatched listing ignored


def test_refresh_rejects_an_implausible_price_jump(db_session, monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    cm.seed_catalog(db_session)
    item = db_session.query(models.ConsumableItem).filter_by(slug="footjoy-weathersof-glove").one()
    item.current_price = 2000
    db_session.commit()
    monkeypatch.setattr(
        rakuten, "search_lowest_price",
        lambda kw: _Listing("FootJoy ウェザーソフ グローブ 12枚セット", price=24000) if "ウェザーソフ" in kw else None,
    )
    cm.refresh_consumable_prices(db_session)
    db_session.refresh(item)
    assert item.current_price == 2000


def test_seed_never_overwrites_an_existing_row(db_session):
    cm.seed_catalog(db_session)
    item = db_session.query(models.ConsumableItem).filter_by(slug="lite-grip-cleaner").one()
    item.msrp = 880
    db_session.commit()
    assert cm.seed_catalog(db_session) == 0
    db_session.refresh(item)
    assert item.msrp == 880


# --- API -------------------------------------------------------------------------------


def test_picks_endpoint_shape(client, db_session, monkeypatch):
    monkeypatch.setattr(cm, "select_picks", lambda db, **kw: ("rainy", [], []))
    resp = client.get("/api/consumables/picks")
    assert resp.status_code == 200
    assert resp.json() == {"season": "rainy", "season_label": "梅雨", "sale_events": [], "picks": []}


def test_refresh_endpoint_requires_admin(client):
    assert client.post("/api/admin/refresh-consumables").status_code in (401, 403)
