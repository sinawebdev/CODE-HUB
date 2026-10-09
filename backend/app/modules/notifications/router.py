"""Read and manage the current user's notifications."""
from fastapi import APIRouter, Query
from app.core.database import DB
from app.core.permissions import VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.notifications import schemas, service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Envelope[schemas.NotificationsOut])
def notifications(user: VerifiedUser, db: DB, limit: int = Query(50, ge=1, le=200)):
    return ok(service.list_notifications(db, user.id, limit))


@router.post("/read-all", response_model=Envelope[None])
def read_all(user: VerifiedUser, db: DB):
    service.mark_all_read(db, user.id)
    return ok(message="All marked read.")


@router.post("/{notification_id}/read", response_model=Envelope[None])
def read(notification_id: str, user: VerifiedUser, db: DB):
    service.mark_read(db, user.id, notification_id)
    return ok(message="Marked read.")


@router.delete("/{notification_id}", response_model=Envelope[None])
def delete(notification_id: str, user: VerifiedUser, db: DB):
    service.delete_notification(db, user.id, notification_id)
    return ok(message="Notification deleted.")
