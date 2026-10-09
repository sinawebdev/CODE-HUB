"""Database tables owned by the profiles module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, UTCDateTime, id_column
from app.core.utils import utcnow


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline: Mapped[str] = mapped_column(String(220), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(150), default="")
    country: Mapped[str] = mapped_column(String(80), default="Ghana")
    region: Mapped[str] = mapped_column(String(80), default="Eastern Region")
    city: Mapped[str] = mapped_column(String(100), default="")
    profile_photo: Mapped[str] = mapped_column(String(32), default="")  # media file id
    cover_photo: Mapped[str] = mapped_column(String(32), default="")  # media file id
    website: Mapped[str] = mapped_column(String(500), default="")
    languages: Mapped[str] = mapped_column(String(500), default="")
    achievements: Mapped[str] = mapped_column(Text, default="")
    interests: Mapped[str] = mapped_column(String(1000), default="")
    services: Mapped[str] = mapped_column(String(1000), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    contact_phone: Mapped[str] = mapped_column(String(40), default="")
    profile_visibility: Mapped[str] = mapped_column(String(20), default="Public")
    contact_visibility: Mapped[str] = mapped_column(String(20), default="Connections")
    location_visibility: Mapped[str] = mapped_column(String(20), default="City")
    completion_pct: Mapped[int] = mapped_column(Integer, default=20)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class Skill(CreatedAtMixin, Base):
    """Catalogue of every skill name ever added (used by search)."""

    __tablename__ = "skills"

    id: Mapped[str] = id_column("SKL")
    name: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(60), default="General")


class UserSkill(CreatedAtMixin, Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_name"),)

    id: Mapped[str] = id_column("USK")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(80))
    level: Mapped[str] = mapped_column(String(30), default="Intermediate")
    endorsements: Mapped[int] = mapped_column(Integer, default=0)


class Experience(CreatedAtMixin, Base):
    __tablename__ = "experiences"

    id: Mapped[str] = id_column("EXP")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    company: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(150), default="")
    start_date: Mapped[str] = mapped_column(String(20), default="")  # YYYY-MM from <input type=month>
    end_date: Mapped[str] = mapped_column(String(20), default="")
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(String(2000), default="")


class Education(CreatedAtMixin, Base):
    __tablename__ = "educations"

    id: Mapped[str] = id_column("EDU")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    school: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str] = mapped_column(String(200), default="")
    field: Mapped[str] = mapped_column(String(200), default="")
    start_year: Mapped[str] = mapped_column(String(10), default="")
    end_year: Mapped[str] = mapped_column(String(10), default="")
    description: Mapped[str] = mapped_column(String(2000), default="")


class Certification(CreatedAtMixin, Base):
    __tablename__ = "certifications"

    id: Mapped[str] = id_column("CRT")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str] = mapped_column(String(200), default="")
    issue_date: Mapped[str] = mapped_column(String(20), default="")
    credential_id: Mapped[str] = mapped_column(String(120), default="")
    credential_url: Mapped[str] = mapped_column(String(500), default="")


class Project(CreatedAtMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = id_column("PRJ")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    start_date: Mapped[str] = mapped_column(String(20), default="")
    end_date: Mapped[str] = mapped_column(String(20), default="")
