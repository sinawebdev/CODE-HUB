"""Database tables owned by the opportunities module (SQLAlchemy models)."""
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, id_column


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = id_column("JOB")
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    posted_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(String(1000), default="")  # comma separated, as entered
    salary: Mapped[str] = mapped_column(String(200), default="")
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="GHS")
    employment_type: Mapped[str] = mapped_column(String(30), default="Full-time")
    experience_level: Mapped[str] = mapped_column(String(30), default="Mid")
    deadline: Mapped[date | None] = mapped_column(Date)
    work_arrangement: Mapped[str] = mapped_column(String(30), default="On-site")
    location_id: Mapped[str | None] = mapped_column(ForeignKey("company_locations.id", ondelete="SET NULL"))
    city: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(80), default="")
    country: Mapped[str] = mapped_column(String(80), default="Ghana")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="Open", index=True)
    views: Mapped[int] = mapped_column(Integer, default=0)


class JobSkill(CreatedAtMixin, Base):
    __tablename__ = "job_skills"

    id: Mapped[str] = id_column("JSK")
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(80))
    required: Mapped[bool] = mapped_column(Boolean, default=True)


class JobApplication(TimestampMixin, Base):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_id", "user_id"),)

    id: Mapped[str] = id_column("APP")
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    cv_file_id: Mapped[str] = mapped_column(String(32), default="")
    cover_letter: Mapped[str] = mapped_column(String(4000), default="")
    status: Mapped[str] = mapped_column(String(20), default="Applied")
    stage: Mapped[str] = mapped_column(String(20), default="Applicants")


class SavedJob(CreatedAtMixin, Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("job_id", "user_id"),)

    id: Mapped[str] = id_column("SJB")
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class JobAlert(CreatedAtMixin, Base):
    __tablename__ = "job_alerts"

    id: Mapped[str] = id_column("JAL")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    keywords: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    employment_type: Mapped[str] = mapped_column(String(30), default="")
    work_arrangement: Mapped[str] = mapped_column(String(30), default="")
    min_salary: Mapped[float | None] = mapped_column(Float)
    frequency: Mapped[str] = mapped_column(String(20), default="Daily")


class Event(CreatedAtMixin, Base):
    __tablename__ = "events"

    id: Mapped[str] = id_column("EVT")
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text, default="")
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[str] = mapped_column(String(20), default="")
    end_time: Mapped[str] = mapped_column(String(20), default="")
    location_name: Mapped[str] = mapped_column(String(250), default="")
    address: Mapped[str] = mapped_column(String(400), default="")
    city: Mapped[str] = mapped_column(String(100), default="Koforidua")
    region: Mapped[str] = mapped_column(String(80), default="Eastern Region")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    cover_image: Mapped[str] = mapped_column(String(32), default="")  # media file id
    registration_required: Mapped[bool] = mapped_column(Boolean, default=False)
    max_attendees: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active | Cancelled | Completed


class EventAttendee(CreatedAtMixin, Base):
    __tablename__ = "event_attendees"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Mapped[str] = id_column("EAT")
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Attending")  # Attending | Maybe | Declined
