import pytest
from sqlalchemy import text

from app.core.database_connection import make_database_engine, parse_database_url


def test_supabase_dashboard_url_keeps_encoded_credentials_and_ssl():
    value = "postgresql://postgres.example:p%40ss%25word@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=verify-full&sslrootcert=root.crt"
    url = parse_database_url(value)
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss%word"
    engine = make_database_engine(value)
    try:
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        assert kwargs["sslmode"] == "verify-full"
        assert kwargs["sslrootcert"] == "root.crt"
        assert engine.pool.size() == 5
    finally:
        engine.dispose()


@pytest.mark.parametrize("mode", ["disable", "allow", "prefer"])
def test_supabase_rejects_plaintext_fallback(mode):
    with pytest.raises(ValueError, match="sslmode"):
        make_database_engine(f"postgresql://postgres:password@db.example.supabase.co/postgres?sslmode={mode}")


def test_transaction_pooler_disables_prepared_statements(monkeypatch):
    from app.core import database_connection

    captured = {}
    monkeypatch.setattr(database_connection, "create_engine", lambda url, **options: captured.update(options))
    make_database_engine("postgresql://postgres.example:password@aws-0-eu-west-1.pooler.supabase.com:6543/postgres")
    assert captured["connect_args"] == {"connect_timeout": 10, "sslmode": "require", "prepare_threshold": None}


def test_migration_refuses_transaction_pooler():
    with pytest.raises(ValueError, match="MIGRATION_DATABASE_URL"):
        make_database_engine("postgresql://postgres.example:password@aws-0-eu-west-1.pooler.supabase.com:6543/postgres", migration=True)


def test_sqlite_connection_still_executes_queries():
    engine = make_database_engine("sqlite://")
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
