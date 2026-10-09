"""Business rules for companies. Other modules may import from here, never from models.py."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import ADMIN_ROLES
from app.modules.companies.models import Company, CompanyLocation, CompanyMember
from app.modules.media import service as media_service

ACTIVE = "Active"
MANAGER_ROLES = ("Owner", "Admin")


# ================================================================ public interface (used by other modules)
# Keep these signatures stable: feed, opportunities, admin, search and analytics call them.

def get_company(db: Session, company_id: str | None) -> Company | None:
    return db.get(Company, company_id) if company_id else None


def can_manage(db: Session, user, company: Company | None) -> bool:
    """Owner, platform admins, or an active member with the Owner/Admin company role."""
    if user is None or company is None:
        return False
    if company.owner_id == user.id or user.role in ADMIN_ROLES:
        return True
    return db.scalar(select(CompanyMember.id).where(
        CompanyMember.company_id == company.id, CompanyMember.user_id == user.id,
        CompanyMember.status == ACTIVE, CompanyMember.role.in_(MANAGER_ROLES),
    ).limit(1)) is not None


def company_summaries(db: Session, company_ids) -> dict[str, dict]:
    """Small company badges for posts, jobs and events: {id, name, logo, verified, industry}."""
    ids = {i for i in company_ids if i}
    if not ids:
        return {}
    return {
        c.id: {"id": c.id, "name": c.name, "logo": media_service.media_url(c.logo),
               "verified": c.verified, "industry": c.industry}
        for c in db.scalars(select(Company).where(Company.id.in_(ids)))
    }


def member_company_ids(db: Session, user_id: str) -> set[str]:
    return set(db.scalars(select(CompanyMember.company_id).where(
        CompanyMember.user_id == user_id, CompanyMember.status == ACTIVE)))


def get_location(db: Session, location_id: str | None) -> CompanyLocation | None:
    return db.get(CompanyLocation, location_id) if location_id else None


def location_summaries(db: Session, location_ids) -> dict[str, dict]:
    ids = {i for i in location_ids if i}
    if not ids:
        return {}
    return {
        loc.id: {"id": loc.id, "name": loc.name, "city": loc.city, "address": loc.address,
                 "region": loc.region, "latitude": loc.latitude, "longitude": loc.longitude}
        for loc in db.scalars(select(CompanyLocation).where(CompanyLocation.id.in_(ids)))
    }


# ================================================================ company pages, members, workplaces

from collections import defaultdict
from sqlalchemy import func, or_
from app.core.errors import forbidden, not_found
from app.core.utils import safe_url, slugify
from app.modules.companies.models import CompanyOffering
from app.modules.identity import service as identity_service
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service


def require_company(db, company_id, user=None, manage=False):
    company = get_company(db, company_id)
    if company is None:
        raise not_found("Company not found.")
    if manage and not can_manage(db, user, company):
        raise forbidden("Not allowed.")
    return company


def hydrate_companies(db, companies, viewer_id=None):
    companies = list(companies)
    ids = [c.id for c in companies]
    if not ids:
        return []
    locations = defaultdict(list)
    for loc in db.scalars(select(CompanyLocation).where(
            CompanyLocation.company_id.in_(ids), CompanyLocation.status != "Deleted")):
        locations[loc.company_id].append(loc)
    members = defaultdict(list)
    for member in db.scalars(select(CompanyMember).where(
            CompanyMember.company_id.in_(ids), CompanyMember.status == ACTIVE)):
        members[member.company_id].append(member)
    result = []
    for c in companies:
        locs = locations[c.id]
        hq = next((l for l in locs if l.is_hq), locs[0] if locs else None)
        result.append({
            "id": c.id, "name": c.name, "slug": c.slug, "industry": c.industry,
            "description": c.description, "website": safe_url(c.website), "email": c.email,
            "phone": c.phone, "founded": c.founded, "size": c.size,
            "logo": media_service.media_url(c.logo), "logoId": c.logo,
            "cover": media_service.media_url(c.cover), "coverId": c.cover,
            "verified": c.verified, "status": c.status, "ownerId": c.owner_id,
            "createdAt": c.created_at, "locationCount": len(locs),
            "hq": {k: getattr(hq, k) for k in ("city", "region", "country", "address")} if hq else None,
            "employeeCount": len(members[c.id]), "jobCount": 0,
            "isMember": any(m.user_id == viewer_id for m in members[c.id]),
            "isOwner": bool(viewer_id and c.owner_id == viewer_id),
        })
    return result


def create_company(db, user, data):
    data = dict(data)
    title = data.pop("your_title") or "Owner"
    data["website"] = safe_url(data["website"])
    company = Company(**data, slug=slugify(data["name"]), owner_id=user.id)
    db.add(company)
    db.flush()
    db.add(CompanyMember(company_id=company.id, user_id=user.id, role="Owner", title=title))
    identity_service.promote_to_employer(db, user)
    platform_service.audit(db, user.id, "CREATE_COMPANY", "Company", company.id, company.name)
    db.commit()
    return hydrate_companies(db, [company], user.id)[0]


def update_company(db, user, company_id, data):
    company = require_company(db, company_id, user, True)
    for key, value in data.items():
        setattr(company, key, safe_url(value) if key == "website" else value or "")
    db.commit()
    return hydrate_companies(db, [company], user.id)[0]


def set_image(db, user, company_id, kind, file_id):
    company = require_company(db, company_id, user, True)
    folder = "Company Photos" if kind == "cover" else "Company Logos"
    file = media_service.owned_file(db, user.id, file_id, (folder,))
    if not file.mime_type.startswith("image/"):
        from app.core.errors import bad_request
        raise bad_request("Invalid file. Please upload it again.", "INVALID_FILE")
    setattr(company, kind, file.id)
    db.commit()
    return media_service.media_url(file.id)


def list_companies(db, viewer_id=None, query="", industry="", limit=60):
    stmt = select(Company).where(Company.status == ACTIVE)
    if query:
        stmt = stmt.where(or_(*(c.icontains(query, autoescape=True) for c in
                               (Company.name, Company.industry, Company.description))))
    if industry:
        stmt = stmt.where(func.lower(Company.industry) == industry.lower())
    rows = hydrate_companies(db, db.scalars(stmt), viewer_id)
    return sorted(rows, key=lambda c: -c["employeeCount"])[:limit]


def my_companies(db, user):
    ids = member_company_ids(db, user.id)
    return hydrate_companies(db, db.scalars(select(Company).where(Company.id.in_(ids))), user.id)


def company_detail(db, company_id, viewer):
    from app.modules.companies.service_locations import hydrate_locations
    company = require_company(db, company_id)
    data = hydrate_companies(db, [company], viewer.id if viewer else None)[0]
    members = list(db.scalars(select(CompanyMember).where(
        CompanyMember.company_id == company_id, CompanyMember.status == ACTIVE)))
    cards = profiles_service.user_cards(db, [m.user_id for m in members])
    data["members"] = [
        {"userId": m.user_id, "name": cards[m.user_id]["name"],
         "title": m.title or cards[m.user_id]["headline"], "role": m.role,
         "photo": cards[m.user_id]["photo"], "verified": cards[m.user_id]["verified"]}
        for m in members if m.user_id in cards
    ]
    data["locations"] = hydrate_locations(db, db.scalars(select(CompanyLocation).where(
        CompanyLocation.company_id == company_id, CompanyLocation.status != "Deleted")))
    data["services"] = [
        {"id": s.id, "name": s.name, "description": s.description}
        for s in db.scalars(select(CompanyOffering).where(CompanyOffering.company_id == company_id))
    ]
    data["canManage"] = can_manage(db, viewer, company)
    return data


def add_offering(db, user, company_id, data):
    require_company(db, company_id, user, True)
    db.add(CompanyOffering(company_id=company_id, **data))
    db.commit()


def search_companies(db, query, viewer_id, limit=12):
    """Router/search composition supplies jobCount using opportunities.open_job_counts."""
    return list_companies(db, viewer_id, query, limit=limit)


def company_stats(db):
    return {"companies": db.scalar(select(func.count()).select_from(Company).where(Company.status == ACTIVE)),
            "locations": db.scalar(select(func.count()).select_from(CompanyLocation).where(
                CompanyLocation.status != "Deleted"))}


def company_member_count(db, company_id):
    return db.scalar(select(func.count()).select_from(CompanyMember).where(
        CompanyMember.company_id == company_id, CompanyMember.status == ACTIVE))


def _admin_rows(db, model, mapping, query="", status="", limit=100):
    stmt = select(model).order_by(model.created_at.desc())
    if status:
        stmt = stmt.where(model.status == status)
    if query:
        stmt = stmt.where(or_(model.id.icontains(query, autoescape=True),
                              model.name.icontains(query, autoescape=True)))
    return [{key: getattr(row, attr) for key, attr in mapping.items()}
            for row in db.scalars(stmt.limit(min(max(limit, 1), 300)))]


def list_companies_admin(db, query="", status="", limit=100):
    mapping = {"CompanyID": "id", "Name": "name", "Slug": "slug", "Industry": "industry",
               "Description": "description", "Website": "website", "Email": "email", "Phone": "phone",
               "Founded": "founded", "Size": "size", "Logo": "logo", "Cover": "cover",
               "OwnerID": "owner_id", "Verified": "verified", "Status": "status",
               "CreatedAt": "created_at", "UpdatedAt": "updated_at"}
    return _admin_rows(db, Company, mapping, query, status, limit)


def list_locations_admin(db, query="", status="", limit=100):
    mapping = {"LocationID": "id", "CompanyID": "company_id", "Name": "name", "Address": "address",
               "Country": "country", "Region": "region", "City": "city", "Area": "area",
               "GhanaPostGPS": "ghana_post_gps", "Landmark": "landmark", "Latitude": "latitude",
               "Longitude": "longitude", "Phone": "phone", "Email": "email",
               "OpeningTime": "opening_time", "ClosingTime": "closing_time", "IsHQ": "is_hq",
               "Status": "status", "CreatedAt": "created_at", "UpdatedAt": "updated_at"}
    return _admin_rows(db, CompanyLocation, mapping, query, status, limit)


def set_company_status(db, company_id, status):
    company = get_company(db, company_id)
    if company is None:
        return False
    company.status = status
    return True


def set_company_verified(db, company_id, verified):
    company = get_company(db, company_id)
    if company is None:
        return False
    company.verified = verified
    return True
