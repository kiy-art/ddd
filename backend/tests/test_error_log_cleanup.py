import datetime

from app import crud


def _insert_log(db_session, level, days_old, source="price_fetch", message="test"):
    log = crud.create_error_log(db_session, source=source, message=message, level=level)
    # create_error_log always stamps "now" via the DB server_default - backdate
    # it directly so cleanup's age-based cutoff has something to act on.
    log.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=days_old)
    db_session.commit()
    return log


def test_cleanup_deletes_only_rows_older_than_the_level_specific_cutoff(db_session):
    _insert_log(db_session, "info", days_old=20)
    _insert_log(db_session, "info", days_old=1)
    _insert_log(db_session, "warning", days_old=20)
    _insert_log(db_session, "error", days_old=20)  # younger than the 30-day error cutoff
    _insert_log(db_session, "error", days_old=40)

    deleted = crud.cleanup_error_logs(db_session, {"info": 14, "warning": 14, "error": 30})
    assert deleted == {"info": 1, "warning": 1, "error": 1}

    remaining = crud.list_error_logs(db_session, limit=100)
    assert len(remaining) == 2
    levels_remaining = sorted(log.level for log in remaining)
    assert levels_remaining == ["error", "info"]


def test_cleanup_ignores_levels_not_named_in_retention_days(db_session):
    _insert_log(db_session, "warning", days_old=999)

    deleted = crud.cleanup_error_logs(db_session, {"info": 14, "error": 30})
    assert deleted == {"info": 0, "error": 0}
    assert len(crud.list_error_logs(db_session, limit=100)) == 1


def test_zero_day_retention_deletes_every_row_of_that_level(db_session):
    """The manual "AI自動修復" action uses a 0-day window for info/warning -
    that must clear rows created moments ago too, not just old ones."""
    crud.create_error_log(db_session, source="price_fetch", message="fresh", level="info")

    deleted = crud.cleanup_error_logs(db_session, {"info": 0})
    assert deleted == {"info": 1}
    assert crud.list_error_logs(db_session, limit=100) == []


def test_count_error_logs_by_level(db_session):
    crud.create_error_log(db_session, source="price_fetch", message="a", level="error")
    crud.create_error_log(db_session, source="price_fetch", message="b", level="error")
    crud.create_error_log(db_session, source="price_fetch", message="c", level="warning")

    counts = crud.count_error_logs_by_level(db_session)
    assert counts == {"error": 2, "warning": 1}


def test_auto_fix_logs_endpoint_requires_admin_auth(client):
    resp = client.post("/api/admin/auto-fix-logs")
    assert resp.status_code in (401, 403)


def test_auto_fix_logs_endpoint_clears_noise_and_reports_remaining(client, db_session, admin_headers):
    _insert_log(db_session, "info", days_old=1)
    _insert_log(db_session, "warning", days_old=1)
    _insert_log(db_session, "error", days_old=1)  # within the 3-day grace window - kept
    _insert_log(db_session, "error", days_old=10)  # older than 3 days - cleared

    resp = client.post("/api/admin/auto-fix-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["deleted"]["info"] == 1
    assert data["deleted"]["warning"] == 1
    assert data["deleted"]["error"] == 1
    assert data["total_deleted"] == 3
    assert data["remaining_by_level"] == {"error": 1}
