"""Company workplaces, photos, and proximity searches."""
from collections import defaultdict
from urllib.parse import quote
from sqlalchemy import delete, select, update
from app.core.errors import bad_request, forbidden, not_found
from app.core.utils import haversine_km
from app.modules.companies import service
from app.modules.companies.models import Company, CompanyLocation, LocationPhoto
from app.modules.media import service as media_service
from app.modules.platform import service as platform_service


def hydrate_locations(db, locations):
    locations = list(locations)
    photos = defaultdict(list)
    ids = [l.id for l in locations]
    if ids:
        for p in db.scalars(select(LocationPhoto).where(LocationPhoto.location_id.in_(ids))):
            photos[p.location_id].append({"id": p.id, "fileId": p.file_id,
                "url": media_service.media_url(p.file_id), "category": p.category, "caption": p.caption})
    result = []
    for loc in locations:
        has_coords = loc.latitude is not None and loc.longitude is not None
        query = f"{loc.latitude},{loc.longitude}" if has_coords else ", ".join(
            v for v in (loc.name, loc.address, loc.city, loc.region, loc.country) if v)
        query = quote(query or "Koforidua", safe="")
        data = {key: getattr(loc, key) for key in (
            "id", "name", "address", "country", "region", "city", "area", "landmark",
            "latitude", "longitude", "phone", "email")}
        data.update(companyId=loc.company_id, ghanaPostGps=loc.ghana_post_gps,
                    openingTime=loc.opening_time, closingTime=loc.closing_time, isHQ=loc.is_hq,
                    photos=photos[loc.id], photoCount=len(photos[loc.id]),
                    mapsLink=f"https://www.google.com/maps/search/?api=1&query={query}",
                    directionsLink=f"https://www.google.com/maps/dir/?api=1&destination={query}")
        result.append(data)
    return result


def require_location(db, user, location_id):
    loc = service.get_location(db, location_id)
    if loc is None or loc.status == "Deleted":
        raise not_found("Workplace not found.")
    if not service.can_manage(db, user, service.get_company(db, loc.company_id)):
        raise forbidden("Not allowed.")
    return loc


def _clear_hq(db, company_id):
    db.execute(update(CompanyLocation).where(CompanyLocation.company_id == company_id).values(is_hq=False))


def add_location(db, user, company_id, data):
    service.require_company(db, company_id, user, True)
    data = dict(data)
    for field, setting in (("country", "defaultCountry"), ("region", "defaultRegion"), ("city", "defaultCity")):
        data[field] = data[field] or platform_service.get_setting(db, setting)
    if data["is_hq"]:
        _clear_hq(db, company_id)
    loc = CompanyLocation(company_id=company_id, **data)
    db.add(loc)
    db.flush()
    platform_service.audit(db, user.id, "CREATE_LOCATION", "CompanyLocation", loc.id, company_id)
    db.commit()
    return hydrate_locations(db, [loc])[0]


def update_location(db, user, location_id, data):
    loc = require_location(db, user, location_id)
    if data.get("is_hq"):
        _clear_hq(db, loc.company_id)
    for key, value in data.items():
        setattr(loc, key, value if key in ("latitude", "longitude") else value or (False if key == "is_hq" else ""))
    db.commit()
    return hydrate_locations(db, [loc])[0]


def delete_location(db, user, location_id):
    loc = require_location(db, user, location_id)
    loc.status = "Deleted"
    db.execute(delete(LocationPhoto).where(LocationPhoto.location_id == location_id))
    platform_service.audit(db, user.id, "DELETE_LOCATION", "CompanyLocation", loc.id, loc.company_id)
    db.commit()


def add_photo(db, user, location_id, data):
    loc = require_location(db, user, location_id)
    file = media_service.owned_file(db, user.id, data["file_id"], ("Workplace Photos",))
    if not file.mime_type.startswith("image/"):
        raise bad_request("Invalid file. Please upload it again.", "INVALID_FILE")
    db.add(LocationPhoto(location_id=loc.id, company_id=loc.company_id, file_id=file.id,
                         category=data["category"] or "General", caption=data["caption"]))
    db.commit()
    return media_service.media_url(file.id)


def delete_photo(db, user, photo_id):
    photo = db.get(LocationPhoto, photo_id)
    if photo is None:
        raise not_found("Photo not found.")
    if not service.can_manage(db, user, service.get_company(db, photo.company_id)):
        raise forbidden("Not allowed.")
    db.delete(photo)
    db.commit()


def nearby_companies(db, viewer_id, lat, lng, radius_km=10):
    companies = list(db.scalars(select(Company).where(Company.status == "Active")))
    ids = [c.id for c in companies]
    best = {}
    for loc in db.scalars(select(CompanyLocation).where(
            CompanyLocation.company_id.in_(ids), CompanyLocation.status != "Deleted")):
        distance = haversine_km(lat, lng, loc.latitude, loc.longitude)
        if distance is not None and distance <= radius_km:
            if loc.company_id not in best or distance < best[loc.company_id][0]:
                best[loc.company_id] = (distance, loc)
    locations = {l["id"]: l for l in hydrate_locations(db, [x[1] for x in best.values()])}
    result = service.hydrate_companies(db, [c for c in companies if c.id in best], viewer_id)
    for row in result:
        distance, loc = best[row["id"]]
        row.update(distance=round(distance, 1), nearLocation=locations[loc.id])
    return sorted(result, key=lambda row: row["distance"])
