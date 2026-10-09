"""Job applications, private CV access, and alerts."""
import logging
from sqlalchemy import select
from app.core import email, events
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.utils import is_past, time_ago
from app.modules.companies import service as companies_service
from app.modules.identity import service as identity_service
from app.modules.media import service as media_service
from app.modules.opportunities import service
from app.modules.opportunities.models import Job, JobAlert, JobApplication
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service

logger = logging.getLogger(__name__)


def apply_job(db, user, job_id, data):
    job = service.require_job(db, job_id)
    if job.status != "Open":
        raise conflict("This job is no longer accepting applications.", "CLOSED")
    if is_past(job.deadline):
        raise conflict("The application deadline has passed.", "DEADLINE_PASSED")
    if db.scalar(select(JobApplication.id).where(
            JobApplication.job_id == job_id, JobApplication.user_id == user.id)):
        raise conflict("You have already applied for this job.")
    cv = data["cv_file_id"]
    if cv:
        cv = media_service.owned_file(db, user.id, cv, ("CVs",)).id
    application = JobApplication(job_id=job.id, user_id=user.id,
                                cv_file_id=cv, cover_letter=data["cover_letter"])
    db.add(application)
    db.flush()
    events.publish(events.JOB_APPLICATION_SUBMITTED, db, applicant=user, job_id=job.id,
                   job_title=job.title, employer_id=job.posted_by, application_id=application.id)
    platform_service.audit(db, user.id, "APPLY_JOB", "Job", job.id, "")
    db.commit()
    try:
        employer = identity_service.get_user(db, job.posted_by)
        if employer and employer.email and platform_service.is_enabled(db, "emailNotifications"):
            email.send_new_application(employer.email, user.full_name, job.title)
    except Exception:
        logger.exception("Unable to deliver new application email for %s", job.id)
    return application.id


def require_application(db, application_id):
    application = db.get(JobApplication, application_id)
    if application is None:
        raise not_found("Application not found.")
    return application


def withdraw_application(db, user, application_id):
    application = require_application(db, application_id)
    if application.user_id != user.id:
        raise forbidden("Not allowed.")
    if application.status in ("Hired", "Rejected"):
        raise bad_request("This application can no longer be withdrawn.")
    application.status = application.stage = "Withdrawn"
    db.commit()


def update_application_status(db, user, application_id, status):
    application = require_application(db, application_id)
    job = service.require_job(db, application.job_id, user, True)
    if status not in service.APPLICATION_STATUSES:
        raise bad_request("Invalid application status.")
    application.status = status
    application.stage = "Applicants" if status == "Applied" else status
    events.publish(events.APPLICATION_STATUS_CHANGED, db, actor=user,
                   applicant_id=application.user_id, job_id=job.id, job_title=job.title, status=status)
    db.commit()


def my_applications(db, user):
    applications = list(db.scalars(select(JobApplication).where(
        JobApplication.user_id == user.id).order_by(JobApplication.created_at.desc())))
    jobs = {j.id: j for j in db.scalars(select(Job).where(Job.id.in_([a.job_id for a in applications])))}
    companies = companies_service.company_summaries(db, [j.company_id for j in jobs.values()])
    result = []
    for application in applications:
        job = jobs.get(application.job_id)
        if job is None:
            continue
        company = companies.get(job.company_id)
        result.append({"id": application.id, "status": application.status, "stage": application.stage,
                       "createdAt": application.created_at, "timeAgo": time_ago(application.created_at),
                       "job": {"id": job.id, "title": job.title, "city": job.city},
                       "company": {k: company[k] for k in ("id", "name", "logo")} if company else None})
    return result


def job_applicants(db, user, job_id):
    service.require_job(db, job_id, user, True)
    applications = list(db.scalars(select(JobApplication).where(
        JobApplication.job_id == job_id).order_by(JobApplication.created_at.desc())))
    cards = profiles_service.user_cards(db, [a.user_id for a in applications])
    return [{"id": a.id, "status": a.status, "stage": a.stage, "coverLetter": a.cover_letter,
             "cvUrl": media_service.signed_url(a.cv_file_id), "cvFileId": a.cv_file_id,
             "createdAt": a.created_at, "timeAgo": time_ago(a.created_at),
             "applicant": {**{k: cards[a.user_id][k] for k in
                             ("userId", "name", "headline", "photo", "city")},
                           "email": cards[a.user_id]["contactEmail"]}}
            for a in applications if a.user_id in cards]


def create_alert(db, user, data):
    data = dict(data)
    data["frequency"] = data["frequency"] or "Daily"
    db.add(JobAlert(user_id=user.id, **data))
    db.commit()
