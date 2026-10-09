"""Thin job, application, and event HTTP endpoints."""
from fastapi import APIRouter, Query
from app.core.database import DB
from app.core.permissions import OptionalUser, VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.opportunities import schemas, service
from app.modules.opportunities import service_applications as applications, service_events as events

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post("/jobs", status_code=201, response_model=Envelope[schemas.JobOut])
def create_job(body: schemas.JobIn, user: VerifiedUser, db: DB):
    return ok(service.create_job(db, user, body.model_dump()), "Job published.")


@router.get("/jobs", response_model=Envelope[list[schemas.JobOut]])
def list_jobs(db: DB, viewer: OptionalUser, query: str = "", city: str = "", sort: str = "newest",
              employment_type: str = Query("", alias="employmentType"),
              work_arrangement: str = Query("", alias="workArrangement"),
              experience_level: str = Query("", alias="experienceLevel"),
              company_id: str = Query("", alias="companyId"), limit: int = Query(60, ge=1, le=300)):
    return ok(service.list_jobs(db, viewer.id if viewer else None, query, employment_type,
                                work_arrangement, experience_level, city, company_id, sort, limit))


@router.get("/jobs/nearby", response_model=Envelope[list[schemas.NearbyJobOut]])
def nearby_jobs(db: DB, viewer: OptionalUser, lat: float = Query(ge=-90, le=90),
                lng: float = Query(ge=-180, le=180),
                radius_km: float = Query(15, alias="radiusKm", gt=0, le=1000),
                employment_type: str = Query("", alias="employmentType"),
                work_arrangement: str = Query("", alias="workArrangement")):
    return ok(service.jobs_nearby(db, viewer.id if viewer else None, lat, lng,
                                 radius_km, employment_type, work_arrangement))


@router.get("/jobs/saved", response_model=Envelope[list[schemas.JobOut]])
def saved_jobs(user: VerifiedUser, db: DB):
    return ok(service.saved_jobs(db, user))


@router.get("/jobs/{job_id}", response_model=Envelope[schemas.JobOut])
def get_job(job_id: str, db: DB, viewer: OptionalUser):
    return ok(service.job_page(db, job_id, viewer.id if viewer else None))


@router.patch("/jobs/{job_id}", response_model=Envelope[schemas.JobOut])
def update_job(job_id: str, body: schemas.JobUpdateIn, user: VerifiedUser, db: DB):
    return ok(service.update_job(db, user, job_id, body.model_dump(exclude_unset=True)), "Job updated.")


@router.post("/jobs/{job_id}/applications", status_code=201, response_model=Envelope[schemas.ApplicationIdOut])
def apply_job(job_id: str, body: schemas.ApplicationIn, user: VerifiedUser, db: DB):
    return ok({"applicationId": applications.apply_job(db, user, job_id, body.model_dump())}, "Application submitted.")


@router.get("/jobs/{job_id}/applications", response_model=Envelope[list[schemas.ApplicationOut]])
def get_applicants(job_id: str, user: VerifiedUser, db: DB):
    return ok(applications.job_applicants(db, user, job_id))


@router.put("/jobs/{job_id}/save", response_model=Envelope[schemas.SavedOut])
def save_job(job_id: str, user: VerifiedUser, db: DB):
    saved, message = service.save_job(db, user, job_id)
    return ok({"saved": saved}, message)


@router.delete("/jobs/{job_id}/save", response_model=Envelope[schemas.SavedOut])
def unsave_job(job_id: str, user: VerifiedUser, db: DB):
    saved, message = service.save_job(db, user, job_id, False)
    return ok({"saved": saved}, message)


@router.get("/applications/mine", response_model=Envelope[list[schemas.MyApplicationOut]])
def my_applications(user: VerifiedUser, db: DB):
    return ok(applications.my_applications(db, user))


@router.post("/applications/{application_id}/withdraw", response_model=Envelope[None])
def withdraw_application(application_id: str, user: VerifiedUser, db: DB):
    applications.withdraw_application(db, user, application_id)
    return ok(None, "Application withdrawn.")


@router.patch("/applications/{application_id}", response_model=Envelope[None])
def update_application(application_id: str, body: schemas.ApplicationStatusIn, user: VerifiedUser, db: DB):
    applications.update_application_status(db, user, application_id, body.status)
    return ok(None, "Application status updated.")


@router.post("/job-alerts", status_code=201, response_model=Envelope[None])
def create_alert(body: schemas.JobAlertIn, user: VerifiedUser, db: DB):
    applications.create_alert(db, user, body.model_dump())
    return ok(None, "Job alert created.")


@router.post("/events", status_code=201, response_model=Envelope[schemas.EventOut])
def create_event(body: schemas.EventIn, user: VerifiedUser, db: DB):
    return ok(events.create_event(db, user, body.model_dump()), "Event created.")


@router.get("/events", response_model=Envelope[list[schemas.EventOut]])
def list_events(db: DB, query: str = "", city: str = "", upcoming: bool = False):
    return ok(events.list_events(db, query, city, upcoming))


@router.get("/events/mine", response_model=Envelope[list[schemas.EventOut]])
def my_events(user: VerifiedUser, db: DB):
    return ok(events.my_events(db, user))


@router.get("/events/{event_id}", response_model=Envelope[schemas.EventPageOut])
def get_event(event_id: str, db: DB, viewer: OptionalUser):
    return ok(events.event_page(db, event_id, viewer))


@router.patch("/events/{event_id}", response_model=Envelope[schemas.EventOut])
def update_event(event_id: str, body: schemas.EventUpdateIn, user: VerifiedUser, db: DB):
    return ok(events.update_event(db, user, event_id, body.model_dump(exclude_unset=True)), "Event updated.")


@router.delete("/events/{event_id}", response_model=Envelope[None])
def delete_event(event_id: str, user: VerifiedUser, db: DB):
    events.delete_event(db, user, event_id)
    return ok(None, "Event cancelled.")


@router.put("/events/{event_id}/attendance", response_model=Envelope[schemas.AttendanceOut])
def attendance(event_id: str, body: schemas.AttendanceIn, user: VerifiedUser, db: DB):
    status, message = events.attendance(db, user, event_id, body.status)
    return ok({"status": status}, message)


@router.delete("/events/{event_id}/attendance", response_model=Envelope[schemas.AttendanceOut])
def cancel_attendance(event_id: str, user: VerifiedUser, db: DB):
    status, message = events.attendance(db, user, event_id, "cancel")
    return ok({"status": status}, message)
