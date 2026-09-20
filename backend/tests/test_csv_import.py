from app import crud
from app.csv_import import import_csv

CSV_OK = b"""product_name,brand,category,model_number,price,product_url,image_url
G440 Driver,PING,driver,G440,70000,https://example.com/g440,https://example.com/g440.jpg
G440 Driver,PING,driver,G440,65000,https://example.com/g440,https://example.com/g440.jpg
Bad Category Item,BrandX,not-a-category,X1,1000,,
"""


def test_import_creates_product_and_records_price(db_session):
    result = import_csv(db_session, CSV_OK)
    assert result.created_products == 1
    assert result.updated_products == 1  # second row for same product updates, not creates
    assert result.prices_recorded == 2
    assert len(result.errors) == 1  # the bad-category row

    product = crud.find_product_by_identity(db_session, "G440 Driver", "PING", "G440")
    assert product is not None
    assert product.current_price == 65000
    history = crud.get_price_history(db_session, product.id)
    assert len(history) == 2


def test_bad_rows_are_logged_and_skipped(db_session):
    import_csv(db_session, CSV_OK)
    logs = crud.list_error_logs(db_session)
    assert any("category" in log.message for log in logs)


def test_missing_required_columns_returns_error():
    class _FakeDb:
        def add(self, *a, **k):
            pass

        def commit(self):
            pass

        def refresh(self, *a, **k):
            pass

    result = import_csv(_FakeDb(), b"foo,bar\n1,2\n")
    assert result.created_products == 0
    assert len(result.errors) == 1
