"""STEP66: the daily job can run in the background (?background=true) and
be polled via /daily-job/status, and never runs twice at once."""

import time

import pytest

from app.config import get_settings
from app.routers import admin as admin_router


@pytest.fixture
def rakuten_configured(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    get_settings.cache_clear()
    monkeypatch.setattr(admin_router.pipeline, "fetch_rakuten_prices", lambda db, on_progress=None: (3, 1))
    monkeypatch.setattr(admin_router.discovery, "discover_new_products", lambda db, on_progress=None: (0, 0))
    monkeypatch.setattr(admin_router.popularity, "sync_popularity_rankings", lambda db: (0, 0))
    monkeypatch.setattr(admin_router.consumables_merchandiser, "refresh_consumable_prices", lambda db: (0, 0))
    yield
    get_settings.cache_clear()


def _wait_until_done(client, headers, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = client.get("/api/admin/daily-job/status", headers=headers).json()
        if state["status"] in ("completed", "failed"):
            return state
        time.sleep(0.1)
    raise AssertionError("daily job did not finish")


def test_background_run_returns_at_once_and_reports_its_result(client, admin_headers, rakuten_configured):
    resp = client.post("/api/admin/fetch-rakuten?background=true", headers=admin_headers)
    assert resp.status_code == 202
    assert resp.json() == {"status": "started"}

    state = _wait_until_done(client, admin_headers)
    assert state["status"] == "completed"
    assert state["error"] is None
    assert state["result"]["prices_updated"] == 3
    assert state["result"]["prices_skipped"] == 1
    assert state["finished_at"] is not None


def test_a_second_start_while_running_is_refused(client, admin_headers, rakuten_configured):
    assert admin_router._claim_daily_job()  # a run is in progress
    for url in ("/api/admin/fetch-rakuten?background=true", "/api/admin/fetch-rakuten"):
        resp = client.post(url, headers=admin_headers)
        assert resp.status_code == 409
        assert resp.json()["status"] == "already_running"


def test_a_background_crash_is_reported_as_failed(client, admin_headers, rakuten_configured, monkeypatch):
    def _crash(db, settings):
        raise RuntimeError("database went away")

    monkeypatch.setattr(admin_router, "_run_daily_job", _crash)
    assert client.post("/api/admin/fetch-rakuten?background=true", headers=admin_headers).status_code == 202
    state = _wait_until_done(client, admin_headers)
    assert state["status"] == "failed"
    assert "database went away" in state["error"]
    # Not stuck: the next day's run can start.
    monkeypatch.undo()


def test_sync_run_still_returns_the_result_and_frees_the_lock(client, admin_headers, rakuten_configured):
    resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["prices_updated"] == 3
    assert client.get("/api/admin/daily-job/status", headers=admin_headers).json()["status"] == "completed"


def test_status_requires_admin(client):
    assert client.get("/api/admin/daily-job/status").status_code in (401, 403)
