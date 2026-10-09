"""Business rules for feed. Other modules may import from here, never from models.py."""
import math
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import events
from app.core.errors import bad_request, forbidden, not_found
from app.core.roles import is_staff
from app.core.utils import time_ago, utcnow
from app.modules.companies import service as companies_service
from app.modules.feed.models import Comment, Post, PostMedia, Reaction, SavedPost
from app.modules.media import service as media_service
from app.modules.profiles import service as profiles_service
from app.modules.network import service as network_service
from app.modules.platform import service as platform_service

ACTIVE = "Active"
UNKNOWN_AUTHOR = {"userId": "", "name": "Unknown", "headline": "", "photo": "", "verified": False}


# ================================================================ public interface (used by other modules)
# Keep these signatures stable: profiles, companies, search, admin and analytics call them.

def hydrate_posts(db: Session, posts: list[Post], viewer_id: str | None, _depth: int = 0) -> list[dict]:
    """Posts as the UI renders them (the demo's hydratePost_), loading related data in batches."""
    if not posts:
        return []
    ids = [p.id for p in posts]
    blocked = network_service.blocked_user_ids(db, viewer_id) if viewer_id else set()
    authors = profiles_service.user_cards(db, {p.user_id for p in posts})
    companies = companies_service.company_summaries(db, {p.company_id for p in posts})
    likes = dict(db.execute(select(Reaction.post_id, func.count()).where(Reaction.post_id.in_(ids))
                            .group_by(Reaction.post_id)).all())
    mine, saved = {}, set()
    if viewer_id:
        mine = dict(db.execute(select(Reaction.post_id, Reaction.type).where(
            Reaction.post_id.in_(ids), Reaction.user_id == viewer_id)).all())
        saved = set(db.scalars(select(SavedPost.post_id).where(
            SavedPost.post_id.in_(ids), SavedPost.user_id == viewer_id)))
    media: dict[str, list[dict]] = {i: [] for i in ids}
    for m in db.scalars(select(PostMedia).where(PostMedia.post_id.in_(ids)).order_by(PostMedia.sort_order)):
        media[m.post_id].append({"id": m.id, "fileId": m.file_id, "url": media_service.media_url(m.file_id),
                                 "type": m.type, "caption": m.caption})
    originals = {}
    repost_ids = {p.repost_of for p in posts if p.repost_of}
    if repost_ids and _depth < 2:
        found = list(db.scalars(select(Post).where(Post.id.in_(repost_ids), Post.status == ACTIVE,
                                                  Post.user_id.not_in(blocked))))
        originals = {h["id"]: h for h in hydrate_posts(db, found, viewer_id, _depth + 1)}
    out = []
    for p in posts:
        author = authors.get(p.user_id)
        first = media[p.id][0] if media[p.id] else None
        out.append({
            "id": p.id, "content": p.content, "createdAt": p.created_at, "timeAgo": time_ago(p.created_at),
            "likeCount": likes.get(p.id, 0), "commentCount": p.comment_count, "shareCount": p.share_count,
            "viewCount": p.view_count, "liked": p.id in mine, "myReaction": mine.get(p.id, ""),
            "saved": p.id in saved, "mediaType": first["type"] if first else "",
            "mediaUrl": first["url"] if first else "", "media": media[p.id],
            "isMine": bool(viewer_id) and p.user_id == viewer_id,
            "author": {k: author[k] for k in UNKNOWN_AUTHOR} if author else dict(UNKNOWN_AUTHOR),
            "company": companies.get(p.company_id), "repostOf": originals.get(p.repost_of),
        })
    return out


def hydrate_post(db: Session, post: Post, viewer_id: str | None) -> dict:
    return hydrate_posts(db, [post], viewer_id)[0]


def count_user_posts(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Post).where(
        Post.user_id == user_id, Post.status == ACTIVE)) or 0


def company_posts(db: Session, company_id: str, viewer_id: str | None, limit: int = 10) -> list[dict]:
    posts = list(db.scalars(visible_posts(db, viewer_id).where(Post.company_id == company_id)
                            .order_by(Post.created_at.desc()).limit(limit)))
    return hydrate_posts(db, posts, viewer_id)


def company_post_stats(db: Session, company_id: str) -> list[dict]:
    """Active company posts with their engagement numbers, newest first (analytics)."""
    posts = db.scalars(select(Post).where(Post.company_id == company_id, Post.status == ACTIVE)
                       .order_by(Post.created_at.desc()))
    return [{"id": p.id, "content": p.content, "likeCount": p.like_count, "commentCount": p.comment_count,
             "shareCount": p.share_count, "createdAt": p.created_at} for p in posts]


# ================================================================ posts, feed, comments, reactions, saves

def visible_posts(db: Session, viewer_id: str | None):
    stmt = select(Post).where(Post.status == ACTIVE)
    if viewer_id:
        stmt = stmt.where(Post.user_id.not_in(network_service.blocked_user_ids(db, viewer_id)))
    return stmt


def require_post(db: Session, post_id: str, viewer_id: str | None = None, *, lock: bool = False) -> Post:
    stmt = visible_posts(db, viewer_id).where(Post.id == post_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    post = db.scalar(stmt)
    if post is None:
        raise not_found("Post not found.")
    return post


def create_post(db: Session, user, data: dict) -> dict:
    company_id = data.get("company_id") or None
    if company_id and not companies_service.can_manage(db, user, companies_service.get_company(db, company_id)):
        raise forbidden("Not allowed for this company.")
    original_id = data.get("repost_of") or None
    original = require_post(db, original_id, user.id, lock=True) if original_id else None
    for item in data["media"]:
        media_service.owned_file(db, user.id, item["file_id"], ("Post Media",))
    post = Post(user_id=user.id, company_id=company_id, content=data["content"],
                visibility=data.get("visibility") or "Public", repost_of=original_id)
    db.add(post)
    db.flush()
    for index, item in enumerate(data["media"]):
        db.add(PostMedia(post_id=post.id, sort_order=index, **item))
    if original:
        original.share_count += 1
    db.commit()
    return hydrate_post(db, post, user.id)


def update_post(db: Session, user, post_id: str, content: str) -> dict:
    post = require_post(db, post_id, user.id, lock=True)
    if post.user_id != user.id and not is_staff(user.role):
        raise forbidden("Not allowed.")
    post.content, post.updated_at = content, utcnow()
    db.commit()
    return hydrate_post(db, post, user.id)


def delete_post(db: Session, user, post_id: str) -> None:
    post = db.scalar(select(Post).where(Post.id == post_id).with_for_update().execution_options(populate_existing=True))
    if post is None:
        raise not_found("Post not found.")
    if post.user_id != user.id and not is_staff(user.role):
        raise forbidden("Not allowed.")
    post.status, post.updated_at = "Removed", utcnow()
    platform_service.audit(db, user.id, "DELETE_POST", "Post", post.id, "")
    db.commit()


def get_feed(db: Session, user, offset: int = 0, limit: int = 20) -> dict:
    posts = list(db.scalars(visible_posts(db, user.id).order_by(Post.created_at.desc()).limit(500)))
    connections = network_service.connected_user_ids(db, user.id)
    companies = companies_service.member_company_ids(db, user.id)
    skills = profiles_service.skill_map(db, [user.id]).get(user.id, set())
    authors = profiles_service.user_cards(db, {p.user_id for p in posts})
    now = utcnow()

    def score(post):
        hours = (now - post.created_at).total_seconds() / 3600
        recency = max(0, 72 - hours) / 72
        engagement = math.log1p(post.like_count * 2 + post.comment_count * 3 + post.share_count * 4) / 5
        affinity = .35 * (post.user_id in connections) + .15 * (post.user_id == user.id)
        affinity += .25 * (post.company_id in companies)
        author = authors.get(post.user_id, {})
        if user.city and author.get("city", "").lower() == user.city.lower():
            affinity += .1
        affinity += sum(.12 for skill in skills if skill and skill in post.content.lower())
        return recency + engagement * .8 + affinity

    posts.sort(key=score, reverse=True)
    return {"posts": hydrate_posts(db, posts[offset:offset + limit], user.id),
            "hasMore": len(posts) > offset + limit}


def user_posts(db: Session, user_id: str, viewer_id: str | None) -> list[dict]:
    posts = list(db.scalars(visible_posts(db, viewer_id).where(Post.user_id == user_id)
                            .order_by(Post.created_at.desc())))
    return hydrate_posts(db, posts, viewer_id)


def get_post(db: Session, post_id: str, viewer_id: str | None) -> dict:
    post = require_post(db, post_id, viewer_id, lock=True)
    post.view_count += 1
    db.commit()
    return hydrate_post(db, post, viewer_id)


def react(db: Session, user, post_id: str, reaction_type: str) -> tuple[dict, str]:
    post = require_post(db, post_id, user.id, lock=True)
    if reaction_type not in ("like", "love", "celebrate", "support", "insightful"):
        reaction_type = "like"
    existing = db.scalar(select(Reaction).where(Reaction.post_id == post_id, Reaction.user_id == user.id))
    liked, message = True, "Reacted."
    if existing and existing.type == reaction_type:
        db.delete(existing)
        liked, message, reaction_type = False, "Reaction removed.", ""
    elif existing:
        existing.type, message = reaction_type, "Reaction updated."
    else:
        db.add(Reaction(post_id=post_id, user_id=user.id, type=reaction_type))
        events.publish(events.POST_REACTED, db, actor=user, post_id=post_id,
                       post_owner_id=post.user_id, reaction_type=reaction_type)
    db.flush()
    post.like_count = db.scalar(select(func.count()).select_from(Reaction).where(Reaction.post_id == post_id)) or 0
    db.commit()
    return {"liked": liked, "count": post.like_count, "type": reaction_type}, message


def hydrate_comments(db: Session, comments: list[Comment], viewer=None) -> list[dict]:
    authors = profiles_service.user_cards(db, {c.user_id for c in comments})
    return [{"id": c.id, "postId": c.post_id, "parentId": c.parent_comment_id or "", "content": c.content,
             "createdAt": c.created_at, "timeAgo": time_ago(c.created_at),
             "isMine": bool(viewer and (c.user_id == viewer.id or is_staff(viewer.role))),
             "author": {k: authors[c.user_id][k] for k in UNKNOWN_AUTHOR}
             if c.user_id in authors else dict(UNKNOWN_AUTHOR)} for c in comments]


def get_comments(db: Session, post_id: str, viewer=None) -> list[dict]:
    require_post(db, post_id, viewer.id if viewer else None)
    stmt = select(Comment).where(Comment.post_id == post_id, Comment.status == ACTIVE)
    if viewer:
        stmt = stmt.where(Comment.user_id.not_in(network_service.blocked_user_ids(db, viewer.id)))
    return hydrate_comments(db, list(db.scalars(stmt.order_by(Comment.created_at))), viewer)


def comment(db: Session, user, post_id: str, content: str, parent_id: str | None) -> dict:
    post = require_post(db, post_id, user.id, lock=True)
    if parent_id:
        parent = db.get(Comment, parent_id)
        if parent is None or parent.post_id != post_id or parent.status != ACTIVE:
            raise bad_request("Parent comment not found.")
    item = Comment(post_id=post_id, user_id=user.id, content=content, parent_comment_id=parent_id or None)
    db.add(item)
    db.flush()
    post.comment_count += 1
    events.publish(events.POST_COMMENTED, db, actor=user, post_id=post_id,
                   post_owner_id=post.user_id, comment_id=item.id)
    db.commit()
    return hydrate_comments(db, [item])[0]


def delete_comment(db: Session, user, comment_id: str) -> None:
    item = db.scalar(select(Comment).where(Comment.id == comment_id).with_for_update()
                     .execution_options(populate_existing=True))
    if item is None:
        raise not_found("Comment not found.")
    if item.user_id != user.id and not is_staff(user.role):
        raise forbidden("Not allowed.")
    if item.status == ACTIVE:
        post = db.scalar(select(Post).where(Post.id == item.post_id).with_for_update()
                         .execution_options(populate_existing=True))
        if post:
            post.comment_count = max(0, post.comment_count - 1)
    item.status = "Deleted"
    db.commit()


def save_post(db: Session, user, post_id: str, save: bool) -> tuple[dict, str]:
    existing = db.scalar(select(SavedPost).where(SavedPost.post_id == post_id, SavedPost.user_id == user.id))
    if not save:
        if existing:
            db.delete(existing)
        message = "Removed from saved."
    elif existing:
        message = "Already saved."
    else:
        require_post(db, post_id, user.id)
        db.add(SavedPost(post_id=post_id, user_id=user.id))
        message = "Post saved."
    db.commit()
    return {"saved": save}, message


def saved_posts(db: Session, user) -> list[dict]:
    posts = list(db.scalars(visible_posts(db, user.id).join(SavedPost, SavedPost.post_id == Post.id)
                            .where(SavedPost.user_id == user.id).order_by(SavedPost.created_at.desc())))
    return hydrate_posts(db, posts, user.id)


def share_post(db: Session, user, post_id: str) -> dict:
    post = require_post(db, post_id, user.id, lock=True)
    post.share_count += 1
    db.commit()
    return {"url": f"#/post/{post_id}"}


def trending(db: Session, viewer_id: str | None) -> dict:
    posts = list(db.scalars(visible_posts(db, viewer_id).where(Post.created_at >= utcnow() - timedelta(days=7))
                            .order_by((Post.like_count * 2 + Post.comment_count * 3 + Post.share_count * 4).desc(),
                                      Post.created_at.desc()).limit(5)))
    return {"posts": hydrate_posts(db, posts, viewer_id), "skills": profiles_service.trending_skills(db)}


def search_posts(db: Session, query: str, viewer_id: str | None, limit: int = 12) -> list[dict]:
    posts = list(db.scalars(visible_posts(db, viewer_id).where(Post.content.icontains(query, autoescape=True))
                            .order_by(Post.created_at.desc()).limit(limit)))
    return hydrate_posts(db, posts, viewer_id)


def post_stats(db: Session) -> dict:
    today = utcnow().date()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    rows = list(db.scalars(select(Post.created_at).where(Post.created_at >= utcnow() - timedelta(days=7))))
    return {"posts": db.scalar(select(func.count()).select_from(Post).where(Post.status == ACTIVE)) or 0,
            "postTrend": [{"label": day.strftime("%m-%d"), "value": sum(t.date() == day for t in rows)}
                          for day in dates]}


def list_posts_admin(db: Session, query: str = "", status: str = "", limit: int = 100) -> list[dict]:
    stmt = select(Post)
    if query:
        stmt = stmt.where(or_(Post.content.icontains(query, autoescape=True), Post.id.icontains(query, autoescape=True)))
    if status:
        stmt = stmt.where(Post.status == status)
    return [{"PostID": p.id, "UserID": p.user_id, "CompanyID": p.company_id or "", "Content": p.content,
             "Visibility": p.visibility, "RepostOf": p.repost_of or "", "LikeCount": p.like_count,
             "CommentCount": p.comment_count, "ShareCount": p.share_count, "ViewCount": p.view_count,
             "Status": p.status, "CreatedAt": p.created_at, "UpdatedAt": p.updated_at}
            for p in db.scalars(stmt.order_by(Post.created_at.desc()).limit(limit))]


def set_post_status(db: Session, post_id: str, status: str) -> bool:
    post = db.get(Post, post_id)
    if post is None:
        return False
    post.status, post.updated_at = status, utcnow()
    return True


def set_comment_status(db: Session, comment_id: str, status: str) -> bool:
    item = db.get(Comment, comment_id)
    if item is None:
        return False
    post = db.get(Post, item.post_id)
    if post and (item.status == ACTIVE) != (status == ACTIVE):
        post.comment_count = max(0, post.comment_count + (1 if status == ACTIVE else -1))
    item.status = status
    return True
