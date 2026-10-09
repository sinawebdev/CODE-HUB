"""HTTP endpoints for stories."""
from fastapi import APIRouter

from app.core.database import DB
from app.core.permissions import OptionalUser, VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.stories import schemas, service

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=Envelope[list[schemas.StoryGroupOut]])
def stories(db: DB, viewer: OptionalUser):
    return ok(service.get_stories(db, viewer.id if viewer else None))


@router.post("", status_code=201, response_model=Envelope[schemas.StoryOut])
def create_story(body: schemas.StoryIn, user: VerifiedUser, db: DB):
    return ok(service.create_story(db, user, body.model_dump()), "Story published.")


@router.post("/{story_id}/view", response_model=Envelope[schemas.ViewOut])
def view_story(story_id: str, user: VerifiedUser, db: DB):
    data, message = service.view_story(db, user, story_id)
    return ok(data, message)


@router.delete("/{story_id}", response_model=Envelope[None])
def delete_story(story_id: str, user: VerifiedUser, db: DB):
    service.delete_story(db, user, story_id)
    return ok(None, "Story deleted.")
