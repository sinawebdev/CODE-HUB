"""Database tables owned by the admin module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, UTCDateTime, id_column


class Report(CreatedAtMixin, Base):
    """A member reporting a user, post, comment, company, job, message or story."""

    __tablename__ = "reports"

    id: Mapped[str] = id_column("RPT")
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(120))
    details: Mapped[str] = mapped_column(String(1500), default="")
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True)
    reviewed_by: Mapped[str] = mapped_column(String(32), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class VerificationRequest(CreatedAtMixin, Base):
    """A request for a verified badge on a profile or a company page."""

    __tablename__ = "verification_requests"

    id: Mapped[str] = id_column("VER")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(20), default="user")  # user | company
    document_file_id: Mapped[str] = mapped_column(String(32), default="")
    notes: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True)
    rejection_reason: Mapped[str] = mapped_column(String(500), default="")
    reviewed_by: Mapped[str] = mapped_column(String(32), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
