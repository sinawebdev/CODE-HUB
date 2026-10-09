"""Manager-only company and job analytics endpoints."""
from fastapi import APIRouter
from app.core.database import DB
from app.core.permissions import VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.analytics import schemas, service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/companies/{company_id}", response_model=Envelope[schemas.CompanyAnalyticsOut])
def company_analytics(company_id: str, user: VerifiedUser, db: DB):
    return ok(service.company_analytics(db, user, company_id))


@router.get("/jobs/{job_id}", response_model=Envelope[schemas.JobAnalyticsOut])
def job_analytics(job_id: str, user: VerifiedUser, db: DB):
    return ok(service.job_analytics(db, user, job_id))
