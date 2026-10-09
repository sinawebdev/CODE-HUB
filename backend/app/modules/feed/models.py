"""Database tables owned by the feed module (SQLAlchemy models)."""
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, id_column


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[str] = id_column("POST")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(20), default="Public")
    repost_of: Mapped[str | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"))
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)  # Active | Removed


class PostMedia(CreatedAtMixin, Base):
    __tablename__ = "post_media"

    id: Mapped[str] = id_column("PMD")
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(20), default="image")  # image | video
    caption: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Comment(CreatedAtMixin, Base):
    __tablename__ = "comments"

    id: Mapped[str] = id_column("CMT")
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_comment_id: Mapped[str | None] = mapped_column(ForeignKey("comments.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(String(2000))
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active | Deleted | Removed


class Reaction(CreatedAtMixin, Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id"),)

    id: Mapped[str] = id_column("RCT")
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), default="like")


class SavedPost(CreatedAtMixin, Base):
    __tablename__ = "saved_posts"
    __table_args__ = (UniqueConstraint("post_id", "user_id"),)

    id: Mapped[str] = id_column("SVP")
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
