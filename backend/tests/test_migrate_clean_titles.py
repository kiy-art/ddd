import importlib.util
import pathlib

from app import crud, models, schemas

_SCRIPT_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "migrate_clean_titles.py"
_spec = importlib.util.spec_from_file_location("migrate_clean_titles", _SCRIPT_PATH)
migrate_clean_titles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate_clean_titles)


def _make_product(db, **overrides):
    defaults = dict(name="Test Driver", brand="PING", category="driver", initial_price=68000)
    defaults.update(overrides)
    return crud.create_product(db, schemas.ProductCreate(**defaults), pending_review=overrides.get("pending_review", False))


def test_dry_run_renames_nothing(db_session):
    product = _make_product(db_session, name="【送料無料】PING G440 ドライバー ポイント10倍!!")

    migrate_clean_titles.run(apply=False, db=db_session)

    db_session.refresh(product)
    assert product.name == "【送料無料】PING G440 ドライバー ポイント10倍!!"


def test_apply_cleans_a_noisy_title(db_session):
    product = _make_product(db_session, name="【送料無料】PING G440 ドライバー ポイント10倍!!")

    migrate_clean_titles.run(apply=True, db=db_session)

    db_session.refresh(product)
    assert product.name == "PING G440 ドライバー"


def test_apply_leaves_an_already_clean_title_unchanged(db_session):
    product = _make_product(db_session, name="PING G440 ドライバー")

    migrate_clean_titles.run(apply=True, db=db_session)

    db_session.refresh(product)
    assert product.name == "PING G440 ドライバー"


def test_apply_merges_duplicates_that_clean_to_the_same_name(db_session):
    survivor_candidate = _make_product(
        db_session,
        name="【送料無料】Titleist Pro V1 ゴルフボール 1ダース",
        brand="Titleist",
        category="ball",
        pending_review=False,
        initial_price=None,
    )
    loser_candidate = _make_product(
        db_session,
        name="Titleist Pro V1 ゴルフボール 1ダース ポイント10倍!!",
        brand="Titleist",
        category="ball",
        pending_review=True,
        initial_price=None,
    )
    crud.add_price(db_session, survivor_candidate, 5600)
    crud.add_price(db_session, loser_candidate, 5400)
    survivor_id, loser_id = survivor_candidate.id, loser_candidate.id

    migrate_clean_titles.run(apply=True, db=db_session)

    remaining = db_session.get(models.Product, survivor_id)
    assert remaining is not None
    assert remaining.name == "Titleist Pro V1 ゴルフボール 1ダース"
    assert db_session.get(models.Product, loser_id) is None

    history = crud.get_price_history(db_session, survivor_id)
    assert sorted(h.price for h in history) == [5400, 5600]


def test_apply_prefers_a_published_product_as_the_merge_survivor(db_session):
    """A pending (unpublished) duplicate must never become the survivor
    over an already-published one - that would accidentally un-publish a
    product that was already live."""
    published = _make_product(
        db_session,
        name="【送料無料】Titleist Pro V1 ゴルフボール 1ダース",
        brand="Titleist",
        category="ball",
        pending_review=False,
    )
    pending = _make_product(
        db_session,
        name="Titleist Pro V1 ゴルフボール 1ダース ポイント10倍!!",
        brand="Titleist",
        category="ball",
        pending_review=True,
    )
    published_id = published.id

    migrate_clean_titles.run(apply=True, db=db_session)

    survivor = db_session.get(models.Product, published_id)
    assert survivor is not None
    assert survivor.pending_review is False
    assert db_session.get(models.Product, pending.id) is None


def test_apply_fills_blank_curated_facts_from_a_merged_loser_without_overwriting(db_session):
    survivor = _make_product(
        db_session,
        name="【送料無料】Titleist Pro V1 ゴルフボール 1ダース",
        brand="Titleist",
        category="ball",
        pending_review=False,
    )
    survivor.msrp = 6000  # already curated - must not be overwritten by the loser's value
    loser = _make_product(
        db_session,
        name="Titleist Pro V1 ゴルフボール 1ダース ポイント10倍!!",
        brand="Titleist",
        category="ball",
        pending_review=True,
    )
    loser.msrp = 6200
    loser.image_url = "https://example.com/provx1.jpg"  # survivor has none - should fill in
    db_session.commit()
    survivor_id = survivor.id

    migrate_clean_titles.run(apply=True, db=db_session)

    remaining = db_session.get(models.Product, survivor_id)
    assert remaining.msrp == 6000  # unchanged, not overwritten
    assert remaining.image_url == "https://example.com/provx1.jpg"  # filled in from the loser
