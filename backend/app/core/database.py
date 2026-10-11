"""Database engine, session and the Base class every model inherits from."""
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings
from app.core.database_connection import make_database_engine
from app.core.utils import new_id, utcnow

engine = make_database_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo, Postgres keeps it)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def id_column(prefix: str) -> Mapped[str]:
    """String primary key with a readable prefix, e.g. USR-3f9a2c1b9d4e7a60."""
    return mapped_column(String(32), primary_key=True, default=lambda: new_id(prefix))


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]
