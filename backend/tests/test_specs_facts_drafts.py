import datetime
import json

from app import crud, models, pipeline, product_facts, schemas, spec_extractor, x_post


def _product(db, name="G440 MAX ドライバー", brand="PING", category="driver", price=68000, **kw):
    p = crud.create_product(db, schemas.ProductCreate(name=name, brand=brand, category=category, initial_price=price))
    for k, v in kw.items():
        setattr(p, k, v)
    db.commit()
    return p


# --- spec extraction ----------------------------------------------------------------


def test_driver_specs_are_read_from_a_typical_caption():
    caption = (
        "【商品詳細】<br>■ロフト角：9°/10.5°<br>■ライ角：59°<br>■ヘッド体積：460cc<br>■長さ：45.75インチ"
        "<br>■シャフト：VENTUS TR 5<br>■フレックス：S/SR<br>■総重量：約303g<br>■送料無料 ポイント10倍"
    )
    specs = spec_extractor.extract_specs(caption, "driver")
    assert specs == {
        "loft": "9°/10.5°",
        "lie": "59°",
        "head_volume": "460cc",
        "length": "45.75インチ",
        "shaft": "VENTUS TR 5",
        "flex": "S/SR",
        "weight": "約303g",
    }


def test_specs_on_one_line_and_in_brackets():
    assert spec_extractor.extract_specs("番手構成：#6-9,PW(5本セット) シャフト：MCI 60 フレックス：R", "iron") == {
        "set": "#6-9,PW(5本セット)",
        "shaft": "MCI 60",
        "flex": "R",
    }
    assert spec_extractor.extract_specs("【ロフト】52°【バンス】12°", "wedge") == {"loft": "52°", "bounce": "12°"}
    assert spec_extractor.extract_specs("構造：4ピース　カバー：ウレタン", "ball") == {"construction": "4ピース", "cover": "ウレタン"}


def test_no_specs_are_invented_from_ad_copy():
    assert spec_extractor.extract_specs("送料無料！ポイント10倍 当店は正規販売店です", "driver") == {}
    assert spec_extractor.extract_specs(None, "driver") == {}
    assert spec_extractor.extract_specs("ロフト角：10.5°", "glove") == {}  # not a field for gloves


def test_price_fetch_stores_specs_without_replacing_existing_ones(db_session, monkeypatch):
    product = _product(db_session, specs_json=json.dumps({"loft": "10.5°"}, ensure_ascii=False))

    class _Result:
        price = 67000
        item_name = "PING G440 MAX ドライバー"
        item_url = "https://item.rakuten.co.jp/x/1/"
        image_url = None
        caption = "ロフト角：9°<br>シャフト：ALTA J CB BLUE"

    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword, **_: _Result())
    pipeline.fetch_rakuten_prices(db_session)
    db_session.refresh(product)
    assert product.specs == {"loft": "10.5°", "shaft": "ALTA J CB BLUE"}


# --- maker facts ----------------------------------------------------------------------


def _row(model, **kw):
    base = dict(brand="PING", model_number=model, msrp=None, release_date=None, skill_level=None,
                performance_type=None, is_current_generation=None)
    base.update(kw)
    return product_facts.FactRow(**base)


def test_facts_match_the_longest_model_in_the_name_and_never_overwrite(db_session):
    max_product = _product(db_session, name="G430 MAX ドライバー 10.5度")
    plain = _product(db_session, name="G430 ドライバー", performance_type="balanced")
    rows = [
        _row("G430", skill_level="all_levels", performance_type="forgiveness"),
        _row("G430 MAX", skill_level="all_levels", performance_type="distance", msrp=93500),
    ]

    preview = product_facts.run_product_facts(db_session, apply=False, rows=rows)
    assert preview.updated == 2
    db_session.refresh(max_product)
    assert max_product.performance_type is None  # dry run wrote nothing

    product_facts.run_product_facts(db_session, apply=True, rows=rows)
    db_session.refresh(max_product)
    db_session.refresh(plain)
    assert (max_product.model_number, max_product.performance_type, max_product.msrp) == ("G430 MAX", "distance", 93500)
    assert plain.performance_type == "balanced"  # an admin's value is kept
    assert plain.skill_level == "all_levels"
    assert product_facts.run_product_facts(db_session, apply=True, rows=rows).updated == 0  # idempotent


def test_the_bundled_facts_csv_loads():
    rows = product_facts.load_facts()
    assert len(rows) > 30
    assert all(r.brand and r.model_number for r in rows)


def test_product_facts_endpoint_requires_admin(client):
    assert client.post("/api/admin/run-product-facts?dry_run=true").status_code in (401, 403)


# --- three X drafts --------------------------------------------------------------------


def test_three_distinct_drafts_morning_noon_evening(db_session, client, admin_headers):
    _product(db_session, name="Qi35 ドライバー", brand="TaylorMade", msrp=99000, price=79000)
    dropped = _product(db_session, name="G440 MAX ドライバー", price=70000)
    crud.add_price(db_session, dropped, 64000)  # previous 70,000 -> now 64,000
    now = datetime.datetime.utcnow()
    for rank, (name, price) in enumerate([("A ドライバー", 50000), ("B ドライバー", 60000), ("C ドライバー", 70000)], 1):
        db_session.add(models.RakutenRankingEntry(category="driver", rank=rank, item_name=name, display_name=name,
                                                  price=price, item_url=f"https://item.rakuten.co.jp/x/{rank}/", fetched_at=now))
    db_session.commit()

    drafts = x_post.build_daily_manual_posts(db_session)
    assert [d.slot for d in drafts] == ["morning", "noon", "evening"]
    morning, noon, evening = drafts
    assert morning.text and "Qi35" in morning.text
    assert noon.text and "値下がり速報" in noon.text and "¥6,000 ダウン" in noon.text and "G440" in noon.text
    assert evening.text and "🥇 A ドライバー ¥50,000" in evening.text and "/popular?category=driver" in evening.text
    assert all(d.weighted_length <= x_post.X_MAX_WEIGHTED_LENGTH for d in drafts)

    body = client.get("/api/admin/x-post-drafts", headers=admin_headers).json()
    assert [d["slot"] for d in body] == ["morning", "noon", "evening"]


def test_drafts_say_why_when_there_is_nothing_to_post(db_session):
    drafts = x_post.build_daily_manual_posts(db_session)
    assert all(d.text is None and d.note for d in drafts)
