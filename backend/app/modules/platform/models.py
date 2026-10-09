"""Database tables owned by the platform module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, UTCDateTime, id_column
from app.core.utils import utcnow


class PlatformSetting(Base):
    """Admin-editable key/value settings (registration open, maintenance mode, branding...)."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class AuditLog(CreatedAtMixin, Base):
    """Who did what to which record. Written by every module through platform.service.audit()."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = id_column("AUD")
    actor_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    target_type: Mapped[str] = mapped_column(String(40), default="")
    target_id: Mapped[str] = mapped_column(String(32), default="")
    details: Mapped[str] = mapped_column(String(1000), default="")
