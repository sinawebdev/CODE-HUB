"""Database tables owned by the identity module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, UTCDateTime, id_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = id_column("USR")
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # stored lowercase
    phone: Mapped[str] = mapped_column(String(40), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="Professional")
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)
    city: Mapped[str] = mapped_column(String(100), default="")
    professional_title: Mapped[str] = mapped_column(String(160), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)  # verified badge
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # bump to revoke all access tokens
    last_login: Mapped[datetime | None] = mapped_column(UTCDateTime)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class RefreshToken(CreatedAtMixin, Base):
    """A login session. The client holds the raw token; we keep only its SHA-256 hash."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = id_column("SES")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    remember: Mapped[bool] = mapped_column(Boolean, default=False)
    user_agent: Mapped[str] = mapped_column(String(250), default="")


class VerificationCode(Base):
    """Current one-time code per user and purpose ('email_verify' or 'password_reset')."""

    __tablename__ = "verification_codes"
    __table_args__ = (UniqueConstraint("user_id", "purpose"),)

    id: Mapped[str] = id_column("OTP")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    code_hash: Mapped[str] = mapped_column(String(64), default="")
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    window_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    window_count: Mapped[int] = mapped_column(Integer, default=0)
