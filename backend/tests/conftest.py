import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_golf_deals.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("ADMIN_API_TOKEN", "test-admin-token")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pathlib  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import progress  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_PATH = pathlib.Path(__file__).parent / "test_golf_deals.db"
engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _fresh_progress_state():
    # app/progress.py is a module-level singleton (see its own docstring)
    # so any test hitting an admin job endpoint (fetch-rakuten, run-update,
    # etc.) leaves state behind for the next test unless it's reset here.
    progress._subscribers.clear()
    progress._current_run = None
    yield
    progress._subscribers.clear()
    progress._current_run = None


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-token"}
