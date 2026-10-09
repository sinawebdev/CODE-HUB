"""Database tables owned by the messaging module (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, UTCDateTime, id_column
from app.core.utils import utcnow


class Conversation(CreatedAtMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = id_column("CNV")
    type: Mapped[str] = mapped_column(String(20), default="direct")  # direct | group
    title: Mapped[str] = mapped_column(String(150), default="")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_message_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id"),)

    id: Mapped[str] = id_column("CVM")
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="Member")  # Owner | Member
    last_read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    muted: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Message(CreatedAtMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = id_column("MSG")
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(String(4000), default="")
    attachment_file_id: Mapped[str] = mapped_column(String(32), default="")
    attachment_type: Mapped[str] = mapped_column(String(20), default="")
    reply_to: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(20), default="Sent")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class MessageReaction(CreatedAtMixin, Base):
    __tablename__ = "message_reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id"),)

    id: Mapped[str] = id_column("MRC")
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), default="like")
