"""HTTP endpoints for feed. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter, Query

from app.core.database import DB
from app.core.permissions import OptionalUser, VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.feed import schemas, service

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=Envelope[schemas.FeedOut])
def feed(user: VerifiedUser, db: DB, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    return ok(service.get_feed(db, user, offset, limit))


@router.get("/trending", response_model=Envelope[schemas.TrendingOut])
def trending(db: DB, viewer: OptionalUser):
    return ok(service.trending(db, viewer.id if viewer else None))


@router.post("/posts", status_code=201, response_model=Envelope[schemas.PostOut])
def create_post(body: schemas.PostIn, user: VerifiedUser, db: DB):
    return ok(service.create_post(db, user, body.model_dump()), "Post published.")


@router.get("/posts", response_model=Envelope[list[schemas.PostOut]])
def user_posts(db: DB, viewer: OptionalUser, user_id: str = Query(alias="userId")):
    return ok(service.user_posts(db, user_id, viewer.id if viewer else None))


@router.get("/posts/saved", response_model=Envelope[list[schemas.PostOut]])
def saved_posts(user: VerifiedUser, db: DB):
    return ok(service.saved_posts(db, user))


@router.get("/posts/{post_id}", response_model=Envelope[schemas.PostOut])
def post(post_id: str, db: DB, viewer: OptionalUser):
    return ok(service.get_post(db, post_id, viewer.id if viewer else None))


@router.patch("/posts/{post_id}", response_model=Envelope[schemas.PostOut])
def update_post(post_id: str, body: schemas.PostUpdateIn, user: VerifiedUser, db: DB):
    return ok(service.update_post(db, user, post_id, body.content), "Post updated.")


@router.delete("/posts/{post_id}", response_model=Envelope[None])
def delete_post(post_id: str, user: VerifiedUser, db: DB):
    service.delete_post(db, user, post_id)
    return ok(None, "Post deleted.")


@router.post("/posts/{post_id}/reactions", response_model=Envelope[schemas.ReactionOut])
def react(post_id: str, body: schemas.ReactionIn, user: VerifiedUser, db: DB):
    data, message = service.react(db, user, post_id, body.type)
    return ok(data, message)


@router.get("/posts/{post_id}/comments", response_model=Envelope[list[schemas.CommentOut]])
def comments(post_id: str, db: DB, viewer: OptionalUser):
    return ok(service.get_comments(db, post_id, viewer))


@router.post("/posts/{post_id}/comments", status_code=201, response_model=Envelope[schemas.CommentOut])
def comment(post_id: str, body: schemas.CommentIn, user: VerifiedUser, db: DB):
    return ok(service.comment(db, user, post_id, body.content, body.parent_id), "Comment added.")


@router.delete("/comments/{comment_id}", response_model=Envelope[None])
def delete_comment(comment_id: str, user: VerifiedUser, db: DB):
    service.delete_comment(db, user, comment_id)
    return ok(None, "Comment deleted.")


@router.put("/posts/{post_id}/save", response_model=Envelope[schemas.SavedOut])
def save_post(post_id: str, user: VerifiedUser, db: DB):
    data, message = service.save_post(db, user, post_id, True)
    return ok(data, message)


@router.delete("/posts/{post_id}/save", response_model=Envelope[schemas.SavedOut])
def unsave_post(post_id: str, user: VerifiedUser, db: DB):
    data, message = service.save_post(db, user, post_id, False)
    return ok(data, message)


@router.post("/posts/{post_id}/share", response_model=Envelope[schemas.ShareOut])
def share_post(post_id: str, user: VerifiedUser, db: DB):
    return ok(service.share_post(db, user, post_id), "Share link ready.")
