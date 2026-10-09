"""HTTP endpoints for media. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.core.database import DB
from app.core.permissions import OptionalUser, VerifiedUser, maintenance_guard
from app.core.schemas import Envelope, ok
from app.modules.media import service
from app.modules.media.schemas import UploadOut

router = APIRouter(prefix="/media", tags=["media"])

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'",
}


@router.post("", status_code=201, response_model=Envelope[UploadOut], dependencies=[Depends(maintenance_guard)])
def upload(user: VerifiedUser, db: DB, folder: str = Form(...), file: UploadFile = File(...)):
    return ok(service.save_upload(db, user.id, folder, file), "Upload complete.")


@router.get("/{file_id}")
def serve(file_id: str, db: DB, viewer: OptionalUser, token: str = "", download: bool = False):
    record, path = service.file_for_download(db, file_id, viewer, token)
    private = record.visibility == "private"
    headers = {**_SECURITY_HEADERS, "Cache-Control": "private, no-store" if private else "public, max-age=86400"}
    as_attachment = download or private or not record.mime_type.startswith(("image/", "video/"))
    return FileResponse(
        path, media_type=record.mime_type, headers=headers,
        filename=record.filename if as_attachment else None,
        content_disposition_type="attachment" if as_attachment else "inline",
    )
