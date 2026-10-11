"""Shared PostgreSQL connection rules for FastAPI and Alembic."""
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import settings


def parse_database_url(value: str) -> URL:
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url


def is_supabase(url: URL) -> bool:
    host = (url.host or "").lower()
    return host.endswith((".supabase.co", ".pooler.supabase.com"))


def is_transaction_pooler(url: URL) -> bool:
    return is_supabase(url) and url.port == 6543


def make_database_engine(value: str, *, migration: bool = False):
    url = parse_database_url(value)
    if migration and is_transaction_pooler(url):
        raise ValueError("Set MIGRATION_DATABASE_URL to a direct or session-pooler connection (port 5432).")
    connect_args = {}
    if url.drivername == "postgresql+psycopg":
        connect_args["connect_timeout"] = 10
        if is_supabase(url):
            sslmode = url.query.get("sslmode", "require")
            if sslmode not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("Supabase connections require sslmode=require or certificate verification.")
            connect_args["sslmode"] = sslmode
        if is_transaction_pooler(url):
            connect_args["prepare_threshold"] = None
    options = {"connect_args": connect_args, "pool_pre_ping": True}
    if migration:
        options["poolclass"] = NullPool
    elif url.get_backend_name() != "sqlite":
        options.update(pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow)
    return create_engine(url, **options)
