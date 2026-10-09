"""Business rules for profiles. Other modules may import from here, never from models.py."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import events
from app.core.errors import conflict, not_found
from app.core.roles import is_staff
from app.core.utils import clean, safe_url
from app.modules.identity import service as identity_service
from app.modules.media import service as media_service
from app.modules.platform import service as platform_service
from app.modules.profiles.models import (
    Certification, Education, Experience, Profile, Project, Skill, UserSkill,
)

VISIBILITY = ("Public", "Connections", "Private")
PHOTO_FOLDERS = {"profile": ("Profile Photos",), "cover": ("Cover Photos",)}
# Profile columns the profile form may edit (account fields go to identity.update_account).
PROFILE_FIELDS = (
    "headline", "about", "location", "country", "region", "city", "website", "languages",
    "achievements", "interests", "services", "contact_email", "contact_phone",
    "profile_visibility", "contact_visibility", "location_visibility",
)


# ---------------------------------------------------------------- creation & lookups

@events.subscribe(events.USER_REGISTERED)
def _create_profile_for_new_user(db: Session, user) -> None:
    create_profile(db, user)


def create_profile(db: Session, user) -> Profile:
    profile = Profile(
        user_id=user.id, headline=user.professional_title, location=user.city, city=user.city,
        country=platform_service.get_setting(db, "defaultCountry"),
        region=platform_service.get_setting(db, "defaultRegion"),
        contact_email=user.email, contact_phone=user.phone, completion_pct=20,
    )
    db.add(profile)
    db.flush()
    return profile


def get_profile(db: Session, user_id: str) -> Profile | None:
    return db.get(Profile, user_id)


def get_or_create_profile(db: Session, user) -> Profile:
    return get_profile(db, user.id) or create_profile(db, user)


def profile_photo_url(db: Session, user_id: str) -> str:
    profile = get_profile(db, user_id)
    return media_service.media_url(profile.profile_photo) if profile else ""


def user_cards(db: Session, user_ids) -> dict[str, dict]:
    """Display data for many users at once (avatars, names, headlines). Missing users are skipped."""
    users = identity_service.get_users(db, user_ids)
    if not users:
        return {}
    profiles = {p.user_id: p for p in db.scalars(select(Profile).where(Profile.user_id.in_(users)))}
    cards = {}
    for uid, user in users.items():
        profile = profiles.get(uid)
        cards[uid] = {
            "userId": uid,
            "name": user.full_name,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "headline": (profile.headline if profile else "") or user.professional_title or "",
            "photo": media_service.media_url(profile.profile_photo if profile else ""),
            "verified": user.verified,
            "city": user.city or "",
            "region": profile.region if profile else "",
            "role": user.role,
            "title": user.professional_title or "",
            "email": user.email,
            "contactEmail": (profile.contact_email if profile else "") or user.email,
            "status": user.status,
        }
    return cards


def user_card(db: Session, user_id: str) -> dict | None:
    return user_cards(db, [user_id]).get(user_id)


def skill_map(db: Session, user_ids) -> dict[str, set[str]]:
    """Lower-cased skill names per user (suggestions, feed relevance)."""
    ids = {i for i in user_ids if i}
    out: dict[str, set[str]] = {i: set() for i in ids}
    if ids:
        for uid, name in db.execute(select(UserSkill.user_id, UserSkill.skill_name).where(UserSkill.user_id.in_(ids))):
            out[uid].add(name.lower())
    return out


def trending_skills(db: Session, limit: int = 8) -> list[dict]:
    rows = db.execute(
        select(func.min(UserSkill.skill_name), func.count())
        .group_by(func.lower(UserSkill.skill_name))
        .order_by(func.count().desc(), func.min(UserSkill.skill_name))
        .limit(limit)
    ).all()
    return [{"name": name, "count": count} for name, count in rows]


def search_skills(db: Session, query: str, limit: int = 12) -> list[dict]:
    stmt = select(Skill).where(Skill.name.icontains(query, autoescape=True)).order_by(Skill.name).limit(limit)
    return [{"id": s.id, "name": s.name, "category": s.category} for s in db.scalars(stmt)]


def user_ids_with_headline(db: Session, query: str, limit: int = 50) -> list[str]:
    stmt = select(Profile.user_id).where(Profile.headline.icontains(query, autoescape=True)).limit(limit)
    return list(db.scalars(stmt))


# ---------------------------------------------------------------- profile page

def _count(db: Session, model, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0


def compute_completion(db: Session, user, profile: Profile) -> int:
    checks = [
        bool(user.first_name and user.last_name), bool(profile.headline), bool(profile.about),
        bool(profile.city), bool(profile.profile_photo), bool(profile.cover_photo),
        _count(db, UserSkill, user.id) > 0, _count(db, Experience, user.id) > 0,
        _count(db, Education, user.id) > 0, bool(profile.website or profile.services),
    ]
    return round(sum(checks) / len(checks) * 100)


def _refresh_completion(db: Session, user) -> None:
    profile = get_or_create_profile(db, user)
    db.flush()
    profile.completion_pct = compute_completion(db, user, profile)


def build_profile(db: Session, user, viewer, *, is_connected: bool, relationship: dict | None, stats: dict) -> dict:
    """The profile page payload. Visibility: Public = everyone, Connections = connections, Private = only you."""
    profile = get_profile(db, user.id) or Profile(user_id=user.id, city=user.city, headline=user.professional_title)
    viewer_id = viewer.id if viewer is not None else None
    is_self = viewer_id == user.id
    can_see_all = is_self or (viewer is not None and is_staff(viewer.role))
    visibility = profile.profile_visibility or "Public"
    if not can_see_all and (visibility == "Private" or (visibility == "Connections" and not is_connected)):
        return {
            "restricted": True,
            "user": {"UserID": user.id, "FirstName": user.first_name, "LastName": user.last_name,
                     "FullName": user.full_name, "Verified": user.verified},
            "message": "This profile is private.",
        }
    contact_vis = profile.contact_visibility or "Connections"
    can_see_contact = can_see_all or contact_vis == "Public" or (contact_vis == "Connections" and is_connected)
    uid = user.id
    experience = db.scalars(select(Experience).where(Experience.user_id == uid)
                            .order_by(Experience.start_date.desc(), Experience.created_at.desc()))
    return {
        "restricted": False,
        "user": identity_service.safe_user(user, include_contact=is_self),
        "profile": {
            "Headline": profile.headline or user.professional_title or "",
            "About": profile.about or "", "Location": profile.location or "",
            "Country": profile.country or "Ghana", "Region": profile.region or "Eastern Region",
            "City": profile.city or user.city or "",
            "ProfilePhoto": profile.profile_photo, "ProfilePhotoUrl": media_service.media_url(profile.profile_photo),
            "CoverPhoto": profile.cover_photo, "CoverPhotoUrl": media_service.media_url(profile.cover_photo),
            "Website": safe_url(profile.website), "Languages": profile.languages or "",
            "Achievements": profile.achievements or "", "Interests": profile.interests or "",
            "Services": profile.services or "",
            "ContactEmail": (profile.contact_email or user.email) if can_see_contact else "",
            "ContactPhone": (profile.contact_phone or user.phone) if can_see_contact else "",
            "ContactVisibility": contact_vis, "Visibility": visibility,
            "CompletionPct": compute_completion(db, user, profile),
        },
        "skills": [{"id": s.id, "name": s.skill_name, "level": s.level, "endorsements": s.endorsements}
                   for s in db.scalars(select(UserSkill).where(UserSkill.user_id == uid).order_by(UserSkill.created_at))],
        "experience": [{"id": e.id, "title": e.title, "company": e.company, "location": e.location,
                        "start": e.start_date, "end": e.end_date, "current": e.current,
                        "description": e.description} for e in experience],
        "education": [{"id": e.id, "school": e.school, "degree": e.degree, "field": e.field,
                       "startYear": e.start_year, "endYear": e.end_year, "description": e.description}
                      for e in db.scalars(select(Education).where(Education.user_id == uid).order_by(Education.created_at))],
        "certifications": [{"id": c.id, "name": c.name, "issuer": c.issuer, "issueDate": c.issue_date,
                            "credentialId": c.credential_id, "url": safe_url(c.credential_url)}
                           for c in db.scalars(select(Certification).where(Certification.user_id == uid)
                                               .order_by(Certification.created_at))],
        "projects": [{"id": p.id, "title": p.title, "description": p.description, "url": safe_url(p.url),
                      "start": p.start_date, "end": p.end_date}
                     for p in db.scalars(select(Project).where(Project.user_id == uid).order_by(Project.created_at))],
        "stats": stats,
        "relationship": relationship if viewer_id and not is_self else None,
    }


# ---------------------------------------------------------------- editing

def update_profile(db: Session, user, changes: dict) -> None:
    """`changes` holds only the fields the client sent (snake_case keys)."""
    profile = get_or_create_profile(db, user)
    for field in PROFILE_FIELDS:
        if field in changes and changes[field] is not None:
            setattr(profile, field, clean(changes[field]))
    if "website" in changes and changes["website"] is not None:
        profile.website = safe_url(changes["website"])
    if changes.get("profile_visibility") is not None and profile.profile_visibility not in VISIBILITY:
        profile.profile_visibility = "Public"
    if changes.get("contact_visibility") is not None and profile.contact_visibility not in VISIBILITY:
        profile.contact_visibility = "Connections"
    for kind, field in (("profile", "profile_photo"), ("cover", "cover_photo")):
        if changes.get(field):
            setattr(profile, field, media_service.owned_file(db, user.id, changes[field], PHOTO_FOLDERS[kind]).id)
    identity_service.update_account(db, user, changes)
    _refresh_completion(db, user)
    db.commit()


def set_photo(db: Session, user, kind: str, file_id: str) -> str:
    kind = "cover" if kind == "cover" else "profile"
    record = media_service.owned_file(db, user.id, file_id, PHOTO_FOLDERS[kind])
    profile = get_or_create_profile(db, user)
    setattr(profile, "cover_photo" if kind == "cover" else "profile_photo", record.id)
    _refresh_completion(db, user)
    db.commit()
    return media_service.media_url(record.id)


def add_skill(db: Session, user, name: str, level: str = "") -> None:
    name = clean(name, 80)
    exists = db.scalar(select(UserSkill.id).where(
        UserSkill.user_id == user.id, func.lower(UserSkill.skill_name) == name.lower()))
    if exists:
        raise conflict("You already have this skill.")
    db.add(UserSkill(user_id=user.id, skill_name=name, level=clean(level, 30) or "Intermediate"))
    if not db.scalar(select(Skill.id).where(func.lower(Skill.name) == name.lower())):
        db.add(Skill(name=name, category="General"))
    _refresh_completion(db, user)
    db.commit()


_ITEMS = {"skills": UserSkill, "experience": Experience, "education": Education,
          "certifications": Certification, "projects": Project}


def add_item(db: Session, user, kind: str, values: dict) -> None:
    """Add an experience/education/certification/project entry; `values` is already validated."""
    db.add(_ITEMS[kind](user_id=user.id, **values))
    _refresh_completion(db, user)
    db.commit()


def delete_item(db: Session, user, kind: str, item_id: str) -> None:
    item = db.get(_ITEMS[kind], item_id)
    if item is None or item.user_id != user.id:
        raise not_found("Not found.")
    db.delete(item)
    _refresh_completion(db, user)
    db.commit()
