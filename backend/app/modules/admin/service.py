"""Business rules for admin. Other modules may import from here, never from models.py."""
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import events
from app.core.email import EmailError, send_verification_decision
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.utils import clean, time_ago, utcnow
from app.modules.admin.models import Report, VerificationRequest
from app.modules.companies import service as companies_service
from app.modules.feed import service as feed_service
from app.modules.identity import service as identity_service
from app.modules.identity import service_admin as users_admin
from app.modules.media import service as media_service
from app.modules.messaging import service as messaging_service
from app.modules.opportunities import service as opportunities_service
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service

logger = logging.getLogger("app.admin")

REPORT_TARGETS = ("User", "Post", "Comment", "Company", "Job", "Message", "Story")
REPORT_STATUSES = ("Pending", "Under Review", "Resolved", "Rejected")
DECISIONS = {"approve": "Approved", "reject": "Rejected", "suspend": "Suspended"}


# ---------------------------------------------------------------- reports

def submit_report(db: Session, user, target_type: str, target_id: str, reason: str, details: str) -> None:
    if target_type not in REPORT_TARGETS:
        raise bad_request("Invalid report target.")
    if not clean(target_id):
        raise bad_request("Missing report target id.")
    if not clean(reason):
        raise bad_request("Please provide a reason.")
    duplicate = db.scalar(select(Report.id).where(
        Report.reporter_id == user.id, Report.target_type == target_type,
        Report.target_id == target_id, Report.status == "Pending").limit(1))
    if duplicate:
        raise conflict("You already reported this.")
    db.add(Report(reporter_id=user.id, target_type=target_type, target_id=clean(target_id, 32),
                  reason=clean(reason, 120), details=clean(details, 1000), status="Pending"))
    platform_service.audit(db, user.id, "REPORT", target_type, target_id, reason)
    db.commit()


def review_report(db: Session, actor, report_id: str, status: str, note: str = "") -> None:
    report = db.get(Report, report_id)
    if report is None:
        raise not_found("Report not found.")
    if status not in REPORT_STATUSES:
        raise bad_request("Invalid report status.")
    if clean(note):
        report.details = f"{report.details} | Note: {clean(note)}"[:1500]
    report.status, report.reviewed_by, report.reviewed_at = status, actor.id, utcnow()
    platform_service.audit(db, actor.id, "REVIEW_REPORT", "Report", report_id, status)
    db.commit()


# ---------------------------------------------------------------- verified badges

def request_verification(db: Session, user, v_type: str, company_id: str | None, note: str) -> None:
    v_type = "company" if v_type == "company" else "user"
    company_id = (clean(company_id) or None) if v_type == "company" else None
    pending = select(VerificationRequest.id).where(
        VerificationRequest.user_id == user.id, VerificationRequest.type == v_type,
        VerificationRequest.status == "Pending")
    if v_type == "company":
        pending = pending.where(VerificationRequest.company_id == company_id)
    if db.scalar(pending.limit(1)):
        raise conflict("You already have a pending request.")
    if v_type == "company":
        company = companies_service.get_company(db, company_id)
        if company is None or not companies_service.can_manage(db, user, company):
            raise forbidden("Not allowed.")
    db.add(VerificationRequest(user_id=user.id, company_id=company_id, type=v_type,
                               notes=clean(note, 1000), status="Pending"))
    db.commit()


def list_verifications(db: Session, status: str = "") -> list[dict]:
    stmt = select(VerificationRequest).order_by(VerificationRequest.created_at.desc())
    if status and status != "All":
        stmt = stmt.where(VerificationRequest.status == status)
    rows = list(db.scalars(stmt))
    cards = profiles_service.user_cards(db, {v.user_id for v in rows})
    companies = companies_service.company_summaries(db, {v.company_id for v in rows})
    out = []
    for v in rows:
        card = cards.get(v.user_id) or {}
        out.append({
            "id": v.id, "userId": v.user_id, "userName": card.get("name", ""),
            "userEmail": card.get("email", ""), "userPhoto": card.get("photo", ""), "userRole": card.get("role", ""),
            "companyId": v.company_id or "", "companyName": (companies.get(v.company_id) or {}).get("name", ""),
            "type": v.type, "documentFileId": v.document_file_id,
            "documentUrl": media_service.signed_url(v.document_file_id), "notes": v.notes, "status": v.status,
            "rejectionReason": v.rejection_reason, "reviewedBy": v.reviewed_by, "reviewedAt": v.reviewed_at,
            "createdAt": v.created_at, "timeAgo": time_ago(v.created_at),
        })
    return out


def review_verification(db: Session, actor, verification_id: str, decision: str, reason: str = "") -> None:
    request = db.get(VerificationRequest, verification_id)
    if request is None:
        raise not_found("Request not found.")
    if decision not in DECISIONS:
        raise bad_request("Invalid decision.")
    status, reason = DECISIONS[decision], clean(reason, 500)
    if status == "Rejected" and not reason:
        raise bad_request("A rejection reason is required.")
    request.status, request.reviewed_by, request.reviewed_at = status, actor.id, utcnow()
    request.rejection_reason = reason if status == "Rejected" else ""
    approved = status == "Approved"
    if request.type == "company" and request.company_id:
        companies_service.set_company_verified(db, request.company_id, approved)
    else:
        users_admin.set_verified(db, request.user_id, approved)
    events.publish(events.VERIFICATION_REVIEWED, db, actor=actor, user_id=request.user_id, status=status, reason=reason)
    platform_service.audit(db, actor.id, "REVIEW_VERIFICATION", "Verification", verification_id,
                           status + (f" | {reason}" if reason else ""))
    db.commit()
    _email_decision(db, request, status, reason)


def _email_decision(db: Session, request: VerificationRequest, status: str, reason: str) -> None:
    target = identity_service.get_user(db, request.user_id)
    if target is None or status == "Suspended" or not platform_service.is_enabled(db, "emailNotifications"):
        return
    company = companies_service.get_company(db, request.company_id) if request.company_id else None
    what = f"company page for {company.name}" if request.type == "company" and company else "profile"
    try:
        send_verification_decision(target.email, target.first_name, status == "Approved", what, reason)
    except EmailError:
        logger.warning("Verification email failed", extra={"user_id": target.id})


# ---------------------------------------------------------------- dashboard and lists

def stats(db: Session) -> dict:
    users = users_admin.user_stats(db)
    opportunities = opportunities_service.opportunity_stats(db)
    posts = feed_service.post_stats(db)
    companies = companies_service.company_stats(db)
    count = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where)) or 0  # noqa: E731
    return {
        "totalUsers": users["totalUsers"], "activeUsers": users["activeUsers"], "newUsers": users["newUsers"],
        "companies": companies["companies"], "jobs": opportunities["jobs"], "totalJobs": opportunities["totalJobs"],
        "applications": opportunities["applications"], "posts": posts["posts"],
        "reports": count(Report, Report.status == "Pending"), "events": opportunities["events"],
        "messages": messaging_service.count_messages(db), "locations": companies["locations"],
        "pendingVerifications": count(VerificationRequest, VerificationRequest.status == "Pending"),
        "unverifiedEmails": users["unverifiedEmails"], "signupTrend": users["signupTrend"],
        "postTrend": posts["postTrend"], "roleBreakdown": users["roleBreakdown"],
    }


def _own_rows(db: Session, model, columns: dict, query: str, status: str, limit: int) -> list[dict]:
    stmt = select(model).order_by(model.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(model.status == status)
    if query:
        stmt = stmt.where(or_(*(getattr(model, attr).icontains(query, autoescape=True)
                                for attr in columns.values() if attr != "created_at")))
    return [{key: getattr(row, attr) for key, attr in columns.items()} for row in db.scalars(stmt)]


_REPORT_COLUMNS = {"ReportID": "id", "ReporterID": "reporter_id", "TargetType": "target_type",
                   "TargetID": "target_id", "Reason": "reason", "Details": "details", "Status": "status",
                   "ReviewedBy": "reviewed_by", "CreatedAt": "created_at"}
_VERIFICATION_COLUMNS = {"VerificationID": "id", "UserID": "user_id", "CompanyID": "company_id", "Type": "type",
                         "Notes": "notes", "Status": "status", "RejectionReason": "rejection_reason",
                         "ReviewedBy": "reviewed_by", "CreatedAt": "created_at"}


def list_resource(db: Session, resource: str, query: str = "", status: str = "", limit: int = 100) -> list[dict]:
    """Raw records for the admin tables (sheet-style keys, newest first)."""
    limit = min(max(limit or 100, 1), 300)
    query, status = clean(query, 100), clean(status, 30)
    listers = {
        "users": lambda: users_admin.list_users_admin(db, query, status, limit),
        "companies": lambda: companies_service.list_companies_admin(db, query, status, limit),
        "jobs": lambda: opportunities_service.list_jobs_admin(db, query, status, limit),
        "posts": lambda: feed_service.list_posts_admin(db, query, status, limit),
        "events": lambda: opportunities_service.list_events_admin(db, query, status, limit),
        "locations": lambda: companies_service.list_locations_admin(db, query, status, limit),
        "applications": lambda: opportunities_service.list_applications_admin(db, query, status, limit),
        "reports": lambda: _own_rows(db, Report, _REPORT_COLUMNS, query, status, limit),
        "verification": lambda: _own_rows(db, VerificationRequest, _VERIFICATION_COLUMNS, query, status, limit),
        "auditlogs": lambda: platform_service.list_audit_logs(db, query, limit),
    }
    lister = listers.get(clean(resource).lower())
    if lister is None:
        raise bad_request("Unknown resource.")
    return lister()


# ---------------------------------------------------------------- moderation of other modules' records

_DELETE = {  # resource: (module, setter name, new status, label, audit action, audit target)
    "posts": (feed_service, "set_post_status", "Removed", "Post", "ADMIN_DELETE", "Post"),
    "comments": (feed_service, "set_comment_status", "Removed", "Comment", "ADMIN_DELETE", "Comment"),
    "jobs": (opportunities_service, "set_job_status", "Closed", "Job", "ADMIN_CLOSE_JOB", "Job"),
    "companies": (companies_service, "set_company_status", "Suspended", "Company", "ADMIN_SUSPEND_COMPANY", "Company"),
    "events": (opportunities_service, "set_event_status", "Cancelled", "Event", "ADMIN_CANCEL_EVENT", "Event"),
}
_DONE = {"posts": "Post removed.", "comments": "Comment removed.", "jobs": "Job closed.",
         "companies": "Company suspended.", "events": "Event cancelled."}
_RESTORE = {
    "posts": (feed_service, "set_post_status", "Active", "Post"),
    "comments": (feed_service, "set_comment_status", "Active", "Comment"),
    "jobs": (opportunities_service, "set_job_status", "Open", "Job"),
    "companies": (companies_service, "set_company_status", "Active", "Company"),
}


def delete_record(db: Session, actor, resource: str, record_id: str) -> str:
    if resource not in _DELETE:
        raise bad_request("Unknown resource.")
    module, setter, status, label, action, target = _DELETE[resource]
    if not getattr(module, setter)(db, record_id, status):
        raise not_found(f"{label} not found.")
    platform_service.audit(db, actor.id, action, target, record_id)
    db.commit()
    return _DONE[resource]


def restore_record(db: Session, actor, resource: str, record_id: str) -> None:
    if resource not in _RESTORE:
        raise bad_request("Unknown resource.")
    module, setter, status, label = _RESTORE[resource]
    if not getattr(module, setter)(db, record_id, status):
        raise not_found(f"{label} not found.")
    platform_service.audit(db, actor.id, "ADMIN_RESTORE", resource, record_id)
    db.commit()
