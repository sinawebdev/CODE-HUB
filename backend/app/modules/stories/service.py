"""Stories, unique views and expiry; related display data is loaded in batches."""
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import forbidden, not_found
from app.core.roles import is_staff
from app.core.utils import utcnow
from app.modules.media import service as media_service
from app.modules.network import service as network_service
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service
from app.modules.stories.models import Story, StoryView


def hydrate_stories(db: Session, stories: list[Story], viewer_id: str | None) -> list[dict]:
    authors = profiles_service.user_cards(db, {s.user_id for s in stories})
    viewed = set(db.scalars(select(StoryView.story_id).where(
        StoryView.story_id.in_([s.id for s in stories]), StoryView.user_id == viewer_id))) if viewer_id else set()
    return [{"id": s.id, "userId": s.user_id,
             "user": {k: authors[s.user_id][k] for k in ("userId", "name", "photo", "verified")},
             "fileId": s.file_id, "url": media_service.media_url(s.file_id), "type": s.type,
             "caption": s.caption, "viewCount": s.view_count, "viewed": s.id in viewed,
             "expiresAt": s.expires_at, "createdAt": s.created_at, "isMine": s.user_id == viewer_id}
            for s in stories if s.user_id in authors]


def create_story(db: Session, user, data: dict) -> dict:
    media_service.owned_file(db, user.id, data["file_id"], ("Stories",))
    story = Story(user_id=user.id, expires_at=utcnow() + timedelta(hours=settings.story_expiry_hours), **data)
    db.add(story)
    db.flush()
    platform_service.audit(db, user.id, "CREATE_STORY", "Story", story.id, "")
    db.commit()
    return hydrate_stories(db, [story], user.id)[0]


def get_stories(db: Session, viewer_id: str | None) -> list[dict]:
    stmt = select(Story).where(Story.status == "Active", Story.expires_at > utcnow())
    if viewer_id:
        stmt = stmt.where(Story.user_id.not_in(network_service.blocked_user_ids(db, viewer_id)))
    stories = list(db.scalars(stmt.order_by(Story.created_at)))
    groups = {}
    for item in hydrate_stories(db, stories, viewer_id):
        uid = item["userId"]
        if uid not in groups:
            groups[uid] = {"userId": uid, "user": item["user"], "storyCount": 0,
                           "hasUnviewed": False, "isMine": uid == viewer_id, "stories": []}
        groups[uid]["stories"].append(item)
        groups[uid]["storyCount"] += 1
        groups[uid]["hasUnviewed"] |= not item["viewed"]
    return sorted(groups.values(), key=lambda g: (not g["isMine"], not g["hasUnviewed"]))


def view_story(db: Session, user, story_id: str) -> tuple[dict, str]:
    story = db.scalar(select(Story).where(Story.id == story_id).with_for_update()
                      .execution_options(populate_existing=True))
    if (story is None or story.status != "Active" or story.expires_at <= utcnow()
            or story.user_id in network_service.blocked_user_ids(db, user.id)):
        raise not_found("Story not found.")
    if story.user_id == user.id:
        return {"viewCount": story.view_count}, "OK"
    existing = db.scalar(select(StoryView.id).where(StoryView.story_id == story_id, StoryView.user_id == user.id))
    if not existing:
        db.add(StoryView(story_id=story_id, user_id=user.id))
        story.view_count += 1
    db.commit()
    return {"viewCount": story.view_count}, "Viewed."


def delete_story(db: Session, user, story_id: str) -> None:
    story = db.scalar(select(Story).where(Story.id == story_id).with_for_update()
                      .execution_options(populate_existing=True))
    if story is None:
        raise not_found("Story not found.")
    if story.user_id != user.id and not is_staff(user.role):
        raise forbidden("Not allowed.")
    story.status = "Deleted"
    db.commit()


def cleanup_expired_stories(db: Session) -> int:
    result = db.execute(update(Story).where(Story.status == "Active", Story.expires_at <= utcnow())
                        .values(status="Expired"))
    db.commit()
    return result.rowcount
