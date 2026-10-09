"""Company and workplace HTTP endpoints."""
from fastapi import APIRouter, Query
from app.core.database import DB
from app.core.permissions import OptionalUser, VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.companies import schemas, service, service_locations as locations
from app.modules.feed import service as feed_service
from app.modules.opportunities import service as opportunities_service

router = APIRouter(prefix="/companies", tags=["companies"])


def with_counts(db, rows):
    counts = opportunities_service.open_job_counts(db, [c["id"] for c in rows])
    for row in rows:
        row["jobCount"] = counts.get(row["id"], 0)
    return rows


@router.post("", status_code=201, response_model=Envelope[schemas.CompanyOut])
def create_company(body: schemas.CompanyIn, user: VerifiedUser, db: DB):
    return ok(with_counts(db, [service.create_company(db, user, body.model_dump())])[0], "Company created.")


@router.get("", response_model=Envelope[list[schemas.CompanyOut]])
def list_companies(db: DB, viewer: OptionalUser, query: str = "", industry: str = "",
                   limit: int = Query(60, ge=1, le=300)):
    return ok(with_counts(db, service.list_companies(db, viewer.id if viewer else None, query, industry, limit)))


@router.get("/mine", response_model=Envelope[list[schemas.CompanyOut]])
def my_companies(user: VerifiedUser, db: DB):
    return ok(with_counts(db, service.my_companies(db, user)))


@router.get("/nearby", response_model=Envelope[list[schemas.NearbyCompanyOut]])
def nearby_companies(db: DB, viewer: OptionalUser, lat: float = Query(ge=-90, le=90),
                     lng: float = Query(ge=-180, le=180),
                     radius_km: float = Query(10, alias="radiusKm", gt=0, le=1000)):
    return ok(with_counts(db, locations.nearby_companies(db, viewer.id if viewer else None, lat, lng, radius_km)))


@router.patch("/locations/{location_id}", response_model=Envelope[schemas.LocationOut])
def update_location(location_id: str, body: schemas.LocationUpdateIn, user: VerifiedUser, db: DB):
    return ok(locations.update_location(db, user, location_id, body.model_dump(exclude_unset=True)), "Workplace updated.")


@router.delete("/locations/{location_id}", response_model=Envelope[None])
def delete_location(location_id: str, user: VerifiedUser, db: DB):
    locations.delete_location(db, user, location_id)
    return ok(None, "Workplace deleted.")


@router.post("/locations/{location_id}/photos", status_code=201, response_model=Envelope[schemas.UrlOut])
def add_photo(location_id: str, body: schemas.PhotoIn, user: VerifiedUser, db: DB):
    return ok({"url": locations.add_photo(db, user, location_id, body.model_dump())}, "Photo added.")


@router.delete("/location-photos/{photo_id}", response_model=Envelope[None])
def delete_photo(photo_id: str, user: VerifiedUser, db: DB):
    locations.delete_photo(db, user, photo_id)
    return ok(None, "Photo deleted.")


@router.get("/{company_id}", response_model=Envelope[schemas.CompanyPageOut])
def company_page(company_id: str, db: DB, viewer: OptionalUser):
    payload = with_counts(db, [service.company_detail(db, company_id, viewer)])[0]
    viewer_id = viewer.id if viewer else None
    payload["jobs"] = opportunities_service.company_jobs(db, company_id, viewer_id)
    payload["events"] = opportunities_service.company_events(db, company_id)
    payload["posts"] = feed_service.company_posts(db, company_id, viewer_id)
    return ok(payload)


@router.patch("/{company_id}", response_model=Envelope[schemas.CompanyOut])
def update_company(company_id: str, body: schemas.CompanyUpdateIn, user: VerifiedUser, db: DB):
    return ok(with_counts(db, [service.update_company(db, user, company_id,
                                                     body.model_dump(exclude_unset=True))])[0], "Company updated.")


@router.put("/{company_id}/image", response_model=Envelope[schemas.UrlOut])
def set_image(company_id: str, body: schemas.ImageIn, user: VerifiedUser, db: DB):
    return ok({"url": service.set_image(db, user, company_id, body.kind, body.file_id)}, "Image updated.")


@router.post("/{company_id}/services", status_code=201, response_model=Envelope[None])
def add_service(company_id: str, body: schemas.OfferingIn, user: VerifiedUser, db: DB):
    service.add_offering(db, user, company_id, body.model_dump())
    return ok(None, "Service added.")


@router.post("/{company_id}/locations", status_code=201, response_model=Envelope[schemas.LocationOut])
def add_location(company_id: str, body: schemas.LocationIn, user: VerifiedUser, db: DB):
    return ok(locations.add_location(db, user, company_id, body.model_dump()), "Workplace added.")
