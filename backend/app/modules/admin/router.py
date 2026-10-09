"""HTTP endpoints for admin. Keep these thin: validate input, call service, return schema.

Staff endpoints live under /admin; members submit reports and verification requests at
/reports and /verification-requests.
"""
from typing import Any

from fastapi import APIRouter, Query

from app.core.database import DB
from app.core.errors import not_found
from app.core.permissions import AdminUser, StaffUser, VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.admin import schemas, service
from app.modules.identity import service as identity_service
from app.modules.identity import service_admin as users_admin
from app.modules.platform import service as platform_service

router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------- members

@router.post("/reports", status_code=201, response_model=Envelope[None])
def report(body: schemas.ReportIn, user: VerifiedUser, db: DB):
    service.submit_report(db, user, body.target_type, body.target_id, body.reason, body.details)
    return ok(None, "Report submitted. Thank you.")


@router.post("/verification-requests", status_code=201, response_model=Envelope[None])
def request_verification(body: schemas.VerificationRequestIn, user: VerifiedUser, db: DB):
    service.request_verification(db, user, body.type, body.company_id, body.note)
    return ok(None, "Verification request submitted.")


# ---------------------------------------------------------------- staff

@router.get("/admin/stats", response_model=Envelope[schemas.AdminStatsOut])
def stats(_: StaffUser, db: DB):
    return ok(service.stats(db))


@router.get("/admin/resources/{resource}", response_model=Envelope[list[dict[str, Any]]])
def list_resource(resource: str, _: StaffUser, db: DB, query: str = "", status: str = "",
                  limit: int = Query(100, ge=1, le=300)):
    return ok(service.list_resource(db, resource, query, status, limit))


@router.delete("/admin/resources/{resource}/{record_id}", response_model=Envelope[None])
def delete_record(resource: str, record_id: str, admin: AdminUser, db: DB):
    return ok(None, service.delete_record(db, admin, resource, record_id))


@router.post("/admin/resources/{resource}/{record_id}/restore", response_model=Envelope[None])
def restore_record(resource: str, record_id: str, admin: AdminUser, db: DB):
    service.restore_record(db, admin, resource, record_id)
    return ok(None, "Restored.")


@router.get("/admin/users/{user_id}", response_model=Envelope[schemas.AdminUserOut])
def get_user(user_id: str, _: StaffUser, db: DB):
    user = identity_service.get_user(db, user_id)
    if user is None:
        raise not_found("User not found.")
    return ok(users_admin.admin_user_detail(user))


@router.put("/admin/users/{user_id}/status", response_model=Envelope[None])
def set_user_status(user_id: str, body: schemas.StatusIn, admin: AdminUser, db: DB):
    users_admin.set_user_status(db, admin, user_id, body.status)
    return ok(None, "User status updated.")


@router.put("/admin/users/{user_id}/role", response_model=Envelope[None])
def set_user_role(user_id: str, body: schemas.RoleIn, admin: AdminUser, db: DB):
    users_admin.set_user_role(db, admin, user_id, body.role)
    return ok(None, "Role updated.")


@router.patch("/admin/reports/{report_id}", response_model=Envelope[None])
def review_report(report_id: str, body: schemas.ReportReviewIn, staff: StaffUser, db: DB):
    service.review_report(db, staff, report_id, body.status, body.note)
    return ok(None, "Report updated.")


@router.get("/admin/verifications", response_model=Envelope[list[schemas.VerificationOut]])
def list_verifications(_: StaffUser, db: DB, status: str = ""):
    return ok(service.list_verifications(db, status))


@router.post("/admin/verifications/{verification_id}/review", response_model=Envelope[None])
def review_verification(verification_id: str, body: schemas.VerificationReviewIn, admin: AdminUser, db: DB):
    service.review_verification(db, admin, verification_id, body.decision, body.reason)
    return ok(None, "Verification updated.")


@router.get("/admin/settings", response_model=Envelope[dict[str, str]])
def get_settings(_: AdminUser, db: DB):
    return ok(platform_service.get_settings(db, platform_service.ADMIN_KEYS))


@router.put("/admin/settings", response_model=Envelope[None])
def save_settings(body: schemas.SettingsIn, admin: AdminUser, db: DB):
    platform_service.save_settings(db, admin.id, body.model_dump(by_alias=True, exclude_unset=True))
    return ok(None, "Settings saved.")
