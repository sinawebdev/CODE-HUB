"""Administrative opportunity interfaces and manager analytics."""
from collections import Counter
from datetime import timedelta
from sqlalchemy import func, or_, select
from app.core.utils import utcnow
from app.modules.opportunities.models import Event, Job, JobApplication, SavedJob


def opportunity_stats(db):
    count = lambda model, *conditions: db.scalar(select(func.count()).select_from(model).where(*conditions))
    return {"jobs": count(Job, Job.status == "Open"), "totalJobs": count(Job),
            "applications": count(JobApplication), "events": count(Event, Event.status == "Active")}


def _rows(db, model, mapping, query="", status="", limit=100):
    stmt = select(model).order_by(model.created_at.desc())
    if status:
        stmt = stmt.where(model.status == status)
    if query:
        columns = [model.id, model.title] if hasattr(model, "title") else [model.id, model.user_id, model.job_id]
        stmt = stmt.where(or_(*(col.icontains(query, autoescape=True) for col in columns)))
    return [{key: getattr(row, attr) for key, attr in mapping.items()}
            for row in db.scalars(stmt.limit(min(max(limit, 1), 300)))]


def list_jobs_admin(db, query="", status="", limit=100):
    mapping = {"JobID": "id", "CompanyID": "company_id", "PostedBy": "posted_by", "Title": "title",
               "Description": "description", "Responsibilities": "responsibilities",
               "Requirements": "requirements", "Skills": "skills", "Salary": "salary",
               "SalaryMin": "salary_min", "SalaryMax": "salary_max", "Currency": "currency",
               "EmploymentType": "employment_type", "ExperienceLevel": "experience_level",
               "Deadline": "deadline", "WorkArrangement": "work_arrangement", "LocationID": "location_id",
               "City": "city", "Region": "region", "Country": "country", "Latitude": "latitude",
               "Longitude": "longitude", "Status": "status", "Views": "views",
               "CreatedAt": "created_at", "UpdatedAt": "updated_at"}
    return _rows(db, Job, mapping, query, status, limit)


def list_events_admin(db, query="", status="", limit=100):
    mapping = {"EventID": "id", "Title": "title", "Description": "description",
               "OrganizerID": "organizer_id", "CompanyID": "company_id", "EventDate": "event_date",
               "StartTime": "start_time", "EndTime": "end_time", "LocationName": "location_name",
               "Address": "address", "City": "city", "Region": "region", "Latitude": "latitude",
               "Longitude": "longitude", "CoverImage": "cover_image",
               "RegistrationRequired": "registration_required", "MaxAttendees": "max_attendees",
               "Status": "status", "CreatedAt": "created_at"}
    return _rows(db, Event, mapping, query, status, limit)


def list_applications_admin(db, query="", status="", limit=100):
    mapping = {"ApplicationID": "id", "JobID": "job_id", "UserID": "user_id",
               "CVFileID": "cv_file_id", "CoverLetter": "cover_letter", "Status": "status",
               "Stage": "stage", "CreatedAt": "created_at", "UpdatedAt": "updated_at"}
    rows = _rows(db, JobApplication, mapping, query, status, limit)
    from app.modules.media import service as media_service
    for row in rows:
        row["CVUrl"] = media_service.signed_url(row["CVFileID"])
    return rows


def set_job_status(db, job_id, status):
    row = db.get(Job, job_id)
    if row is None:
        return False
    row.status = status
    return True


def set_event_status(db, event_id, status):
    row = db.get(Event, event_id)
    if row is None:
        return False
    row.status = status
    return True


def company_analytics_base(db, user, company_id):
    from app.modules.companies import service as companies_service
    companies_service.require_company(db, company_id, user, True)
    jobs = list(db.scalars(select(Job).where(Job.company_id == company_id)))
    applications = list(db.scalars(select(JobApplication).where(
        JobApplication.job_id.in_([j.id for j in jobs]))))
    statuses = Counter(a.status for a in applications)
    days = Counter(a.created_at.date() for a in applications)
    today = utcnow().date()
    return {"jobViews": sum(j.views for j in jobs), "jobs": len(jobs), "applications": len(applications),
            "followers": companies_service.company_member_count(db, company_id),
            "applicationTrend": [{"label": (today - timedelta(days=i)).strftime("%m-%d"),
                                  "value": days[today - timedelta(days=i)]} for i in range(6, -1, -1)],
            "pipeline": [{"label": status, "value": statuses[status]}
                         for status in ("Applied", "Shortlisted", "Interview", "Hired", "Rejected")]}


def job_analytics(db, user, job_id):
    from app.modules.opportunities import service
    job = service.require_job(db, job_id, user, True)
    return {"views": job.views,
            "applications": db.scalar(select(func.count()).select_from(JobApplication).where(
                JobApplication.job_id == job_id)),
            "saves": db.scalar(select(func.count()).select_from(SavedJob).where(SavedJob.job_id == job_id))}
