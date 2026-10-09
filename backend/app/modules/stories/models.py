"""Database tables owned by the stories module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, UTCDateTime, id_column


class Story(CreatedAtMixin, Base):
    __tablename__ = "stories"

    id: Mapped[str] = id_column("STR")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(20), default="image")  # image | video
    caption: Mapped[str] = mapped_column(String(300), default="")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active | Deleted | Expired
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class StoryView(CreatedAtMixin, Base):
    __tablename__ = "story_views"
    __table_args__ = (UniqueConstraint("story_id", "user_id"),)

    id: Mapped[str] = id_column("SVW")
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
