"""HTTP endpoints for profiles. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter

from app.core.database import DB
from app.core.errors import not_found
from app.core.permissions import OptionalUser, VerifiedUser
from app.core.roles import ACTIVE, is_staff
from app.core.schemas import Envelope, ok
from app.modules.feed import service as feed_service
from app.modules.identity import service as identity_service
from app.modules.network import service as network_service
from app.modules.profiles import schemas, service

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _page(db, target, viewer) -> dict:
    """Profile payload plus the network/feed numbers that live in other modules."""
    viewer_id = viewer.id if viewer is not None else None
    other = viewer_id is not None and viewer_id != target.id
    stats = {**network_service.network_stats(db, target.id), "posts": feed_service.count_user_posts(db, target.id)}
    return service.build_profile(
        db, target, viewer,
        is_connected=other and network_service.are_connected(db, viewer_id, target.id),
        relationship=network_service.relationship(db, viewer_id, target.id) if other else None,
        stats=stats,
    )


@router.get("/me", response_model=Envelope[schemas.ProfilePageOut])
def my_profile(user: VerifiedUser, db: DB):
    return ok(_page(db, user, user))


@router.patch("/me", response_model=Envelope[schemas.ProfilePageOut])
def update_my_profile(body: schemas.ProfileUpdateIn, user: VerifiedUser, db: DB):
    service.update_profile(db, user, body.model_dump(exclude_unset=True))
    return ok(_page(db, user, user), "Profile updated.")


@router.put("/me/photo", response_model=Envelope[schemas.PhotoOut])
def set_photo(body: schemas.PhotoIn, user: VerifiedUser, db: DB):
    return ok({"url": service.set_photo(db, user, body.kind, body.file_id)}, "Photo updated.")


@router.post("/me/skills", status_code=201, response_model=Envelope[None])
def add_skill(body: schemas.SkillIn, user: VerifiedUser, db: DB):
    service.add_skill(db, user, body.name, body.level)
    return ok(None, "Skill added.")


@router.delete("/me/skills/{item_id}", response_model=Envelope[None])
def remove_skill(item_id: str, user: VerifiedUser, db: DB):
    service.delete_item(db, user, "skills", item_id)
    return ok(None, "Skill removed.")


@router.post("/me/experience", status_code=201, response_model=Envelope[None])
def add_experience(body: schemas.ExperienceIn, user: VerifiedUser, db: DB):
    service.add_item(db, user, "experience", body.model_dump())
    return ok(None, "Experience added.")


@router.post("/me/education", status_code=201, response_model=Envelope[None])
def add_education(body: schemas.EducationIn, user: VerifiedUser, db: DB):
    service.add_item(db, user, "education", body.model_dump())
    return ok(None, "Education added.")


@router.post("/me/certifications", status_code=201, response_model=Envelope[None])
def add_certification(body: schemas.CertificationIn, user: VerifiedUser, db: DB):
    service.add_item(db, user, "certifications", body.model_dump())
    return ok(None, "Certification added.")


@router.post("/me/projects", status_code=201, response_model=Envelope[None])
def add_project(body: schemas.ProjectIn, user: VerifiedUser, db: DB):
    service.add_item(db, user, "projects", body.model_dump())
    return ok(None, "Project added.")


@router.delete("/me/{kind}/{item_id}", response_model=Envelope[None])
def delete_item(kind: str, item_id: str, user: VerifiedUser, db: DB):
    if kind not in ("experience", "education", "certifications", "projects"):
        raise not_found()
    service.delete_item(db, user, kind, item_id)
    return ok(None, "Deleted.")


@router.get("/{user_id}", response_model=Envelope[schemas.ProfilePageOut])
def profile(user_id: str, db: DB, viewer: OptionalUser):
    target = identity_service.get_user(db, user_id)
    if target is None or (target.status != ACTIVE and not (viewer and is_staff(viewer.role))):
        raise not_found("Profile not found.")
    return ok(_page(db, target, viewer))
