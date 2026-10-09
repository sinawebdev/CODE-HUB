"""Jobs and public opportunity interfaces."""
from collections import Counter
from sqlalchemy import delete, func, or_, select
from app.core.errors import bad_request, forbidden, not_found
from app.core.utils import haversine_km, is_past, time_ago
from app.modules.companies import service as companies_service
from app.modules.opportunities.models import Job, JobApplication, JobSkill, SavedJob
from app.modules.platform import service as platform_service

JOB_STATUSES = ("Draft", "Open", "Closed", "Cancelled", "Archived")
APPLICATION_STATUSES = ("Applied", "Shortlisted", "Interview", "Rejected", "Hired", "Withdrawn")


def get_job(db, job_id):
    return db.get(Job, job_id)


def require_job(db, job_id, user=None, manage=False):
    job = get_job(db, job_id)
    if job is None:
        raise not_found("Job not found.")
    if manage and not companies_service.can_manage(
            db, user, companies_service.get_company(db, job.company_id)):
        raise forbidden("Not allowed.")
    return job


def hydrate_jobs(db, jobs, viewer_id=None):
    jobs = list(jobs)
    ids = [j.id for j in jobs]
    if not ids:
        return []
    companies = companies_service.company_summaries(db, [j.company_id for j in jobs])
    locations = companies_service.location_summaries(db, [j.location_id for j in jobs])
    applications = list(db.scalars(select(JobApplication).where(JobApplication.job_id.in_(ids))))
    counts = Counter(a.job_id for a in applications)
    mine = {a.job_id: a for a in applications if a.user_id == viewer_id}
    saved = set(db.scalars(select(SavedJob.job_id).where(
        SavedJob.job_id.in_(ids), SavedJob.user_id == viewer_id))) if viewer_id else set()
    result = []
    for job in jobs:
        loc = locations.get(job.location_id)
        data = {key: getattr(job, key) for key in (
            "id", "title", "description", "responsibilities", "requirements", "salary",
            "currency", "city", "region", "country", "latitude", "longitude", "status", "views")}
        data.update(
            skills=[s.strip() for s in job.skills.split(",") if s.strip()],
            salaryMin=job.salary_min, salaryMax=job.salary_max,
            employmentType=job.employment_type, experienceLevel=job.experience_level,
            deadline=job.deadline, deadlinePassed=is_past(job.deadline),
            workArrangement=job.work_arrangement, createdAt=job.created_at,
            timeAgo=time_ago(job.created_at), saved=job.id in saved, applied=job.id in mine,
            applicationStatus=mine[job.id].status if job.id in mine else "",
            company=companies.get(job.company_id),
            location={k: loc[k] for k in ("id", "name", "city", "address", "region")} if loc else None,
            applicantCount=counts[job.id])
        result.append(data)
    return result


def _sync_skills(db, job):
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    db.add_all([JobSkill(job_id=job.id, skill_name=name.strip()[:80], required=True)
                for name in job.skills.split(",") if name.strip()])


def create_job(db, user, data):
    data = dict(data)
    company = companies_service.get_company(db, data.pop("company_id"))
    if company is None:
        raise bad_request("Please select a company.")
    if not companies_service.can_manage(db, user, company):
        raise forbidden("Not allowed for this company.")
    if is_past(data["deadline"]):
        raise bad_request("Deadline must be in the future.")
    if data["status"] not in JOB_STATUSES:
        data["status"] = "Open"
    location_id = data.pop("location_id")
    location = companies_service.get_location(db, location_id)
    if location_id and (location is None or location.company_id != company.id or location.status == "Deleted"):
        raise bad_request("Invalid workplace.")
    for field, fallback in (("city", "Koforidua"), ("region", "Eastern Region"),
                            ("currency", "GHS"), ("employment_type", "Full-time"),
                            ("experience_level", "Mid"), ("work_arrangement", "On-site")):
        data[field] = data[field] or fallback
    if location:
        data.update(city=location.city, region=location.region, country=location.country,
                    latitude=location.latitude, longitude=location.longitude)
    job = Job(**data, company_id=company.id, posted_by=user.id,
              location_id=location.id if location else None)
    db.add(job)
    db.flush()
    _sync_skills(db, job)
    platform_service.audit(db, user.id, "CREATE_JOB", "Job", job.id, company.name)
    db.commit()
    return hydrate_jobs(db, [job], user.id)[0]


def update_job(db, user, job_id, data):
    job = require_job(db, job_id, user, True)
    if "status" in data and data["status"] not in JOB_STATUSES:
        raise bad_request("Invalid job status.")
    if is_past(data.get("deadline")):
        raise bad_request("Deadline must be in the future.")
    for key, value in data.items():
        setattr(job, key, value if key in ("salary_min", "salary_max", "deadline") else value or "")
    if "skills" in data:
        _sync_skills(db, job)
    db.commit()
    return hydrate_jobs(db, [job], user.id)[0]


def job_page(db, job_id, viewer_id):
    job = require_job(db, job_id)
    job.views += 1
    db.commit()
    return hydrate_jobs(db, [job], viewer_id)[0]


def list_jobs(db, viewer_id=None, query="", employment_type="", work_arrangement="",
              experience_level="", city="", company_id="", sort="newest", limit=60):
    stmt = select(Job).where(Job.status == "Open")
    if query:
        stmt = stmt.where(or_(*(column.icontains(query, autoescape=True) for column in
                               (Job.title, Job.description, Job.skills, Job.city))))
    for field, value in (("employment_type", employment_type), ("work_arrangement", work_arrangement),
                         ("experience_level", experience_level), ("company_id", company_id)):
        if value:
            stmt = stmt.where(getattr(Job, field) == value)
    if city:
        stmt = stmt.where(func.lower(Job.city) == city.lower())
    stmt = stmt.order_by(Job.created_at.asc() if sort == "oldest" else Job.created_at.desc())
    return hydrate_jobs(db, db.scalars(stmt.limit(limit)), viewer_id)


def jobs_nearby(db, viewer_id, lat, lng, radius_km=15, employment_type="", work_arrangement=""):
    stmt = select(Job).where(Job.status == "Open")
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
    if work_arrangement:
        stmt = stmt.where(Job.work_arrangement == work_arrangement)
    jobs = list(db.scalars(stmt))
    locations = companies_service.location_summaries(db, [j.location_id for j in jobs])
    near, distances = [], {}
    for job in jobs:
        loc = locations.get(job.location_id) or {}
        latitude = job.latitude if job.latitude is not None else loc.get("latitude")
        longitude = job.longitude if job.longitude is not None else loc.get("longitude")
        distance = haversine_km(lat, lng, latitude, longitude)
        if distance is not None and distance <= radius_km:
            near.append(job)
            distances[job.id] = round(distance, 1)
    result = hydrate_jobs(db, near, viewer_id)
    for row in result:
        row["distance"] = distances[row["id"]]
    return sorted(result, key=lambda row: row["distance"])


def save_job(db, user, job_id, save=True):
    saved = db.scalar(select(SavedJob).where(SavedJob.job_id == job_id, SavedJob.user_id == user.id))
    if not save:
        if saved:
            db.delete(saved)
        db.commit()
        return False, "Job removed from saved."
    if saved:
        return True, "Already saved."
    require_job(db, job_id)
    db.add(SavedJob(job_id=job_id, user_id=user.id))
    db.commit()
    return True, "Job saved."


def saved_jobs(db, user):
    stmt = select(Job).join(SavedJob, SavedJob.job_id == Job.id).where(
        SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc())
    return hydrate_jobs(db, db.scalars(stmt), user.id)


def open_job_counts(db, company_ids):
    ids = set(company_ids)
    if not ids:
        return {}
    return dict(db.execute(select(Job.company_id, func.count()).where(
        Job.company_id.in_(ids), Job.status == "Open").group_by(Job.company_id)).all())


def company_jobs(db, company_id, viewer_id, limit=20):
    return list_jobs(db, viewer_id, company_id=company_id, limit=limit)


def search_jobs(db, query, viewer_id, limit=12):
    return list_jobs(db, viewer_id, query=query, limit=limit)


# Re-export stable interfaces used by search, admin, analytics, and company routers.
from app.modules.opportunities.service_events import company_events, search_events
from app.modules.opportunities.service_admin import (
    company_analytics_base, job_analytics, list_applications_admin, list_events_admin,
    list_jobs_admin, opportunity_stats, set_event_status, set_job_status,
)
