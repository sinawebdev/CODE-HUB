"""Shared test fixtures.

Every test runs inside one outer transaction that is rolled back afterwards, so services can
call commit() freely. Tests use in-memory SQLite by default; set TEST_DATABASE_URL to run the
same suite against PostgreSQL, e.g.
TEST_DATABASE_URL=postgresql+psycopg://koforlink:koforlink@localhost:5432/koforlink_test
"""
import itertools
import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-that-is-long-enough-for-hs256")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import email as email_module
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules import load_models

load_models()

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
PASSWORD = "Password123!"
PASSWORD_HASH = hash_password(PASSWORD)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


def _make_engine():
    if not TEST_DATABASE_URL.startswith("sqlite"):
        return create_engine(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _connect(dbapi_connection, _record):
        dbapi_connection.isolation_level = None  # SQLAlchemy emits BEGIN itself (needed for SAVEPOINT)
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def _begin(connection):
        connection.exec_driver_sql("BEGIN")

    return engine


@pytest.fixture(scope="session")
def engine():
    engine = _make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint",
                      autoflush=False, expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", tmp_path / "media")
    email_module.OUTBOX.clear()


@pytest.fixture
def outbox():
    return email_module.OUTBOX


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(user) -> dict:
    token, _ = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(db):
    """Create a ready-to-use member: `user = make_user(role="Employer")`, then `client.get(..., headers=user.headers)`."""
    from app.modules.identity.models import User
    from app.modules.profiles import service as profiles_service

    counter = itertools.count(1)

    def factory(*, role="Professional", verified=True, email=None, first_name="Test", last_name=None,
                city="Koforidua", title="Engineer", status="Active"):
        n = next(counter)
        user = User(
            first_name=first_name, last_name=last_name or f"User{n}", email=email or f"user{n}@example.com",
            password_hash=PASSWORD_HASH, role=role, status=status, city=city, professional_title=title,
            email_verified=verified,
        )
        db.add(user)
        db.flush()
        profiles_service.create_profile(db, user)
        db.commit()
        user.headers = auth_headers(user)
        user.password = PASSWORD
        return user

    return factory


def upload(client, user, folder="Post Media", content=PNG, mime="image/png", name="photo.png") -> dict:
    """Upload a file through the API and return its {fileId, url, ...} payload."""
    response = client.post("/api/v1/media", headers=user.headers, data={"folder": folder},
                           files={"file": (name, content, mime)})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def set_setting(db, key: str, value: str) -> None:
    from app.modules.platform.models import PlatformSetting

    row = db.get(PlatformSetting, key)
    if row is None:
        db.add(PlatformSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()
