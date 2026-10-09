"""Business rules for media. Other modules may import from here, never from models.py."""
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, bad_request, forbidden, not_found
from app.core.roles import is_staff
from app.core.security import create_signed_token, verify_signed_token
from app.core.utils import clean, new_id, slugify
from app.modules.media.models import MediaFile

FOLDERS = (
    "Profile Photos", "Cover Photos", "Company Logos", "Company Photos", "Workplace Photos",
    "Post Media", "CVs", "Documents", "Event Images", "Stories",
)
PRIVATE_FOLDERS = ("CVs", "Documents")
ALLOWED_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
    "application/pdf": ".pdf", "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "video/mp4": ".mp4",
}
_CHUNK = 64 * 1024
_SIGNED_PURPOSE = "media"


def _looks_like(head: bytes, mime: str) -> bool:
    """Check the file's first bytes match its declared type, so nothing else is served as an image."""
    checks = {
        "image/jpeg": head.startswith(b"\xff\xd8\xff"),
        "image/png": head.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": head[:6] in (b"GIF87a", b"GIF89a"),
        "image/webp": head[:4] == b"RIFF" and head[8:12] == b"WEBP",
        "application/pdf": head.startswith(b"%PDF"),
        "application/msword": head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": head.startswith(b"PK\x03\x04"),
        "video/mp4": head[4:8] == b"ftyp",
    }
    return checks.get(mime, False)


def media_url(file_id: str | None) -> str:
    """Public URL of a stored file ('' when there is none). Images in the UI use this."""
    return f"{settings.public_base_url}/api/v1/media/{file_id}" if file_id else ""


def download_url(file_id: str | None) -> str:
    return f"{media_url(file_id)}?download=true" if file_id else ""


def signed_url(file_id: str | None, minutes: int = 60) -> str:
    """Time-limited link to a private file (e.g. a CV shown to the employer reviewing it)."""
    if not file_id:
        return ""
    return f"{media_url(file_id)}?token={create_signed_token(file_id, _SIGNED_PURPOSE, minutes)}"


def describe(record: MediaFile) -> dict:
    return {
        "fileId": record.id,
        "url": signed_url(record.id) if record.visibility == "private" else media_url(record.id),
        "downloadUrl": download_url(record.id),
        "name": record.filename,
        "size": record.size_bytes,
    }


def save_upload(db: Session, owner_id: str, folder: str, upload: UploadFile) -> dict:
    if folder not in FOLDERS:
        raise bad_request("Invalid upload folder.")
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_TYPES:
        raise AppError(415, "INVALID_FILE_TYPE", "Unsupported file type.")
    max_bytes = settings.story_max_upload_bytes if folder == "Stories" else settings.max_upload_bytes
    file_id = new_id("MED")
    relative = Path(slugify(folder)) / f"{file_id}{ALLOWED_TYPES[mime]}"
    target = settings.media_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    size, head = 0, b""
    try:
        with target.open("wb") as out:
            while chunk := upload.file.read(_CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise AppError(413, "FILE_TOO_LARGE",
                                   f"File is too large. Maximum size is {round(max_bytes / (1024 * 1024))} MB.")
                if len(head) < 16:
                    head = (head + chunk)[:16]
                out.write(chunk)
        if size == 0:
            raise bad_request("No file data received.")
        if not _looks_like(head, mime):
            raise AppError(415, "INVALID_FILE_TYPE", "Unsupported file type.")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    record = MediaFile(
        id=file_id, owner_id=owner_id, folder=folder, mime_type=mime, size_bytes=size,
        filename=clean(upload.filename, 200) or f"upload{ALLOWED_TYPES[mime]}",
        storage_path=relative.as_posix(),
        visibility="private" if folder in PRIVATE_FOLDERS else "public",
    )
    db.add(record)
    db.commit()
    return describe(record)


def get_file(db: Session, file_id: str | None) -> MediaFile | None:
    return db.get(MediaFile, file_id) if file_id else None


def owned_file(db: Session, owner_id: str, file_id: str | None, folders: tuple[str, ...] = ()) -> MediaFile:
    """A file the caller uploaded (optionally from given folders), or a 400 error."""
    record = get_file(db, clean(file_id, 32))
    if record is None or record.owner_id != owner_id or (folders and record.folder not in folders):
        raise bad_request("Invalid file. Please upload it again.", "INVALID_FILE")
    return record


def file_for_download(db: Session, file_id: str, viewer=None, token: str = "") -> tuple[MediaFile, Path]:
    """Resolve a file for serving. Private files need the owner, staff, or a valid signed token."""
    record = get_file(db, file_id)
    if record is None:
        raise not_found("File not found.")
    if record.visibility == "private":
        allowed = (viewer is not None and (viewer.id == record.owner_id or is_staff(viewer.role))) or (
            bool(token) and verify_signed_token(token, record.id, _SIGNED_PURPOSE))
        if not allowed:
            raise forbidden("You do not have access to this file.")
    path = settings.media_root / record.storage_path
    if not path.is_file():
        raise not_found("File not found.")
    return record, path
