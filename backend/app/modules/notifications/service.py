"""Business rules for notifications. Other modules may import from here, never from models.py."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification
from app.core import events
from app.core.errors import not_found
from app.core.utils import time_ago
from app.modules.profiles import service as profiles_service


# ================================================================ public interface (used by other modules)

def unread_count(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.is_read.is_(False))) or 0


# ================================================================ notifications + event handlers

def list_notifications(db: Session, user_id: str, limit: int = 50) -> dict:
    rows = list(db.scalars(select(Notification).where(Notification.user_id == user_id)
                           .order_by(Notification.created_at.desc()).limit(limit)))
    cards = profiles_service.user_cards(db, {row.actor_id for row in rows if row.actor_id})
    return {"notifications": [
        {"id": row.id, "type": row.type, "title": row.title, "body": row.body, "link": row.link,
         "read": row.is_read, "createdAt": row.created_at, "timeAgo": time_ago(row.created_at),
         "actorPhoto": cards.get(row.actor_id, {}).get("photo", "")} for row in rows],
        "unread": unread_count(db, user_id)}


def _owned(db: Session, user_id: str, notification_id: str) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user_id:
        raise not_found("Not found.")
    return row


def mark_read(db: Session, user_id: str, notification_id: str) -> None:
    _owned(db, user_id, notification_id).is_read = True
    db.commit()


def mark_all_read(db: Session, user_id: str) -> None:
    db.execute(update(Notification).where(Notification.user_id == user_id).values(is_read=True))
    db.commit()


def delete_notification(db: Session, user_id: str, notification_id: str) -> None:
    db.delete(_owned(db, user_id, notification_id))
    db.commit()


def _notify(db: Session, recipient_id: str, kind: str, title: str, body: str, link: str, actor=None) -> None:
    """Join the publisher's transaction; skip notifications addressed to the actor."""
    if not recipient_id or (actor is not None and actor.id == recipient_id):
        return
    db.add(Notification(user_id=recipient_id, type=kind, title=title[:200], body=body[:500],
                        link=link[:300], actor_id=actor.id if actor is not None else None))


@events.subscribe(events.CONNECTION_REQUESTED)
def _connection_requested(db: Session, requester, addressee_id: str, connection_id: str) -> None:
    _notify(db, addressee_id, "connection_request", "New connection request",
            f"{requester.full_name} wants to connect with you.", "#/network", requester)


@events.subscribe(events.CONNECTION_ACCEPTED)
def _connection_accepted(db: Session, accepter, requester_id: str, connection_id: str) -> None:
    _notify(db, requester_id, "connection_accepted", "Connection accepted",
            f"{accepter.full_name} accepted your connection request.", "#/network", accepter)


@events.subscribe(events.USER_FOLLOWED)
def _user_followed(db: Session, follower, following_id: str) -> None:
    _notify(db, following_id, "follow", "New follower",
            f"{follower.full_name} started following you.", "#/network", follower)


@events.subscribe(events.POST_REACTED)
def _post_reacted(db: Session, actor, post_id: str, post_owner_id: str, reaction_type: str) -> None:
    _notify(db, post_owner_id, "reaction", "New reaction",
            f"{actor.full_name} reacted to your post.", f"#/post/{post_id}", actor)


@events.subscribe(events.POST_COMMENTED)
def _post_commented(db: Session, actor, post_id: str, post_owner_id: str, comment_id: str) -> None:
    _notify(db, post_owner_id, "comment", "New comment",
            f"{actor.full_name} commented on your post.", f"#/post/{post_id}", actor)


@events.subscribe(events.JOB_APPLICATION_SUBMITTED)
def _application_submitted(db: Session, applicant, job_id: str, job_title: str,
                           employer_id: str, application_id: str) -> None:
    _notify(db, employer_id, "job_application", "New job application",
            f"{applicant.full_name} applied for {job_title}.", f"#/job/{job_id}", applicant)


@events.subscribe(events.APPLICATION_STATUS_CHANGED)
def _application_updated(db: Session, actor, applicant_id: str, job_id: str, job_title: str, status: str) -> None:
    _notify(db, applicant_id, "application_status", "Application update",
            f"Your application for {job_title} is now: {status}.", f"#/job/{job_id}", actor)


@events.subscribe(events.MESSAGE_SENT)
def _message_sent(db: Session, sender, conversation_id: str, recipient_ids, title: str, preview: str) -> None:
    for recipient_id in set(recipient_ids):
        _notify(db, recipient_id, "message", f"New message from {title}",
                preview or "Sent an attachment", f"#/messages/{conversation_id}", sender)


@events.subscribe(events.VERIFICATION_REVIEWED)
def _verification_reviewed(db: Session, actor, user_id: str, status: str, reason: str) -> None:
    body = f"Your verification request has been {status.lower()}."
    if status == "Rejected" and reason:
        body += f" Reason: {reason}"
    _notify(db, user_id, "verification", f"Verification {status.lower()}", body, "#/settings", actor)


@events.subscribe(events.EMAIL_VERIFIED)
def _email_verified(db: Session, user) -> None:
    _notify(db, user.id, "system", "Welcome to KoforLink",
            "Your email is verified. Complete your profile to get discovered.", "#/profile")
