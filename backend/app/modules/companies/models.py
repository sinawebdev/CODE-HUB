"""Database tables owned by the companies module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, UTCDateTime, id_column
from app.core.utils import utcnow


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[str] = id_column("CMP")
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), index=True)
    industry: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    founded: Mapped[str] = mapped_column(String(20), default="")
    size: Mapped[str] = mapped_column(String(20), default="")
    logo: Mapped[str] = mapped_column(String(32), default="")  # media file id
    cover: Mapped[str] = mapped_column(String(32), default="")  # media file id
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)  # Active | Suspended


class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (UniqueConstraint("company_id", "user_id"),)

    id: Mapped[str] = id_column("CMM")
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="Employee")  # Owner | Admin | Employee
    title: Mapped[str] = mapped_column(String(150), default="")
    status: Mapped[str] = mapped_column(String(20), default="Active")
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class CompanyOffering(CreatedAtMixin, Base):
    """A service a company offers (the demo's CompanyServices sheet)."""

    __tablename__ = "company_offerings"

    id: Mapped[str] = id_column("SRV")
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(800), default="")


class CompanyLocation(TimestampMixin, Base):
    """A workplace: head office, branch, shop, factory..."""

    __tablename__ = "company_locations"

    id: Mapped[str] = id_column("LOC")
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(400), default="")
    country: Mapped[str] = mapped_column(String(80), default="Ghana")
    region: Mapped[str] = mapped_column(String(80), default="Eastern Region")
    city: Mapped[str] = mapped_column(String(100), default="Koforidua")
    area: Mapped[str] = mapped_column(String(150), default="")
    ghana_post_gps: Mapped[str] = mapped_column(String(40), default="")
    landmark: Mapped[str] = mapped_column(String(200), default="")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    opening_time: Mapped[str] = mapped_column(String(20), default="")
    closing_time: Mapped[str] = mapped_column(String(20), default="")
    is_hq: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active | Deleted


class LocationPhoto(CreatedAtMixin, Base):
    __tablename__ = "location_photos"

    id: Mapped[str] = id_column("LPH")
    location_id: Mapped[str] = mapped_column(ForeignKey("company_locations.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(60), default="General")
    caption: Mapped[str] = mapped_column(String(300), default="")
