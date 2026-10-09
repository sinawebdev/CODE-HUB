"""Database tables owned by the media module (SQLAlchemy models)."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, id_column


class MediaFile(CreatedAtMixin, Base):
    __tablename__ = "media_files"

    id: Mapped[str] = id_column("MED")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    folder: Mapped[str] = mapped_column(String(40))  # e.g. "Profile Photos", "CVs"
    filename: Mapped[str] = mapped_column(String(200))  # original name, for downloads
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500))  # relative to settings.media_root
    visibility: Mapped[str] = mapped_column(String(20), default="public")  # public | private
