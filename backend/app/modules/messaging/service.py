"""Business rules for messaging. Other modules may import from here, never from models.py."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.messaging.models import Conversation, ConversationMember, Message, MessageReaction
from app.core import events
from app.core.errors import bad_request, forbidden, not_found
from app.core.roles import is_staff
from app.core.utils import clean, time_ago, utcnow
from app.modules.identity import service as identity_service
from app.modules.media import service as media_service
from app.modules.network import service as network_service
from app.modules.profiles import service as profiles_service


# ================================================================ public interface (used by other modules)

def unread_message_count(db: Session, user_id: str) -> int:
    """Messages from others newer than the user's last read time, across all their conversations."""
    return db.scalar(
        select(func.count()).select_from(Message)
        .join(ConversationMember, ConversationMember.conversation_id == Message.conversation_id)
        .where(
            ConversationMember.user_id == user_id,
            Message.sender_id != user_id,
            or_(ConversationMember.last_read_at.is_(None), Message.created_at > ConversationMember.last_read_at),
        )
    ) or 0


def count_messages(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Message)) or 0


# ================================================================ conversations and messages

def _membership(db: Session, user_id: str, conversation_id: str,
                message: str = "Not a member of this conversation.") -> ConversationMember:
    membership = db.scalar(select(ConversationMember).where(
        ConversationMember.conversation_id == conversation_id, ConversationMember.user_id == user_id))
    if membership is None:
        raise forbidden(message)
    return membership


def hydrate_conversations(db: Session, conversations: list[Conversation], user_id: str) -> list[dict]:
    if not conversations:
        return []
    ids = [row.id for row in conversations]
    members: dict[str, list] = {cid: [] for cid in ids}
    for member in db.scalars(select(ConversationMember).where(ConversationMember.conversation_id.in_(ids))):
        members[member.conversation_id].append(member)
    cards = profiles_service.user_cards(db, {member.user_id for rows in members.values() for member in rows})
    latest, unread = {}, dict.fromkeys(ids, 0)
    memberships = {cid: next((m for m in rows if m.user_id == user_id), None) for cid, rows in members.items()}
    for message in db.scalars(select(Message).where(Message.conversation_id.in_(ids))
                              .order_by(Message.created_at, Message.id)):
        cid = message.conversation_id
        latest[cid] = message
        membership = memberships[cid]
        if message.sender_id != user_id and (membership is None or membership.last_read_at is None
                                            or message.created_at > membership.last_read_at):
            unread[cid] += 1
    out = []
    for row in conversations:
        mine = memberships[row.id]
        other = next((cards.get(m.user_id) for m in members[row.id] if m.user_id != user_id), None)
        title = other["name"] if row.type == "direct" and other else row.title
        last = latest.get(row.id)
        out.append({"id": row.id, "type": row.type, "title": title or "Conversation",
                    "avatar": other["photo"] if row.type == "direct" and other else "",
                    "memberIds": [m.user_id for m in members[row.id]], "memberCount": len(members[row.id]),
                    "lastMessage": {"body": "Message deleted" if last.deleted else last.body,
                                    "senderId": last.sender_id, "createdAt": last.created_at,
                                    "timeAgo": time_ago(last.created_at)} if last else None,
                    "lastMessageAt": row.last_message_at, "unread": unread[row.id],
                    "pinned": mine.pinned if mine else False, "muted": mine.muted if mine else False})
    return out


def hydrate_messages(db: Session, messages: list[Message], user_id: str) -> list[dict]:
    cards = profiles_service.user_cards(db, {message.sender_id for message in messages})
    reactions = {message.id: [] for message in messages}
    if reactions:
        for reaction in db.scalars(select(MessageReaction).where(MessageReaction.message_id.in_(reactions))):
            reactions[reaction.message_id].append({"userId": reaction.user_id, "type": reaction.type})
    return [{"id": row.id, "body": "" if row.deleted else row.body, "deleted": row.deleted,
             "senderId": row.sender_id, "senderName": cards.get(row.sender_id, {}).get("name", "Unknown"),
             "senderPhoto": cards.get(row.sender_id, {}).get("photo", ""), "mine": row.sender_id == user_id,
             "attachmentUrl": "" if row.deleted else media_service.signed_url(row.attachment_file_id),
             "attachmentFileId": "" if row.deleted else row.attachment_file_id,
             "attachmentType": "" if row.deleted else row.attachment_type,
             "replyTo": row.reply_to, "status": row.status, "createdAt": row.created_at,
             "timeAgo": time_ago(row.created_at), "reactions": reactions[row.id]} for row in messages]


def start_conversation(db: Session, user, target_id: str, initial_message: str = "") -> tuple[dict, str]:
    if user.id == target_id:
        raise bad_request("Cannot message yourself.")
    if identity_service.get_user(db, target_id) is None:
        raise not_found("User not found.")
    if network_service.is_blocked(db, user.id, target_id):
        raise forbidden("Unable to message this user.", "BLOCKED")
    mine = select(ConversationMember.conversation_id).where(ConversationMember.user_id == user.id)
    theirs = select(ConversationMember.conversation_id).where(ConversationMember.user_id == target_id)
    conversation = db.scalar(select(Conversation).where(
        Conversation.type == "direct", Conversation.id.in_(mine), Conversation.id.in_(theirs)).limit(1))
    opened = conversation is not None
    if conversation is None:
        conversation = Conversation(type="direct", title="", created_by=user.id)
        db.add(conversation)
        db.flush()
        db.add_all([ConversationMember(conversation_id=conversation.id, user_id=user.id, last_read_at=utcnow()),
                    ConversationMember(conversation_id=conversation.id, user_id=target_id)])
        db.flush()
    if initial_message:
        send_message(db, user, conversation.id, initial_message)
    else:
        db.commit()
    return {"conversationId": conversation.id}, "Conversation opened." if opened else "Conversation started."


def create_group(db: Session, user, member_ids: list[str], title: str = "") -> dict:
    users = identity_service.get_users(db, set(member_ids) - {user.id})
    ids = [uid for uid, member in users.items() if member.status == "Active"]
    if not ids:
        raise bad_request("No valid members selected.")
    if set(ids) & network_service.blocked_user_ids(db, user.id):
        raise forbidden("Unable to message this user.", "BLOCKED")
    conversation = Conversation(type="group", title=clean(title, 150) or "Group chat", created_by=user.id)
    db.add(conversation)
    db.flush()
    db.add(ConversationMember(conversation_id=conversation.id, user_id=user.id, role="Owner", last_read_at=utcnow()))
    db.add_all([ConversationMember(conversation_id=conversation.id, user_id=uid) for uid in ids])
    db.commit()
    return {"conversationId": conversation.id}


def list_conversations(db: Session, user_id: str) -> list[dict]:
    ids = select(ConversationMember.conversation_id).where(ConversationMember.user_id == user_id)
    rows = list(db.scalars(select(Conversation).where(Conversation.id.in_(ids))))
    out = hydrate_conversations(db, rows, user_id)
    return sorted(out, key=lambda row: (row["pinned"], row["lastMessageAt"]), reverse=True)


def get_messages(db: Session, user_id: str, conversation_id: str, since_id: str = "") -> dict:
    membership = _membership(db, user_id, conversation_id)
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    since = db.get(Message, since_id) if since_id else None
    if since and since.conversation_id == conversation_id:
        stmt = stmt.where(or_(Message.created_at > since.created_at,
                             (Message.created_at == since.created_at) & (Message.id > since.id)))
    messages = list(db.scalars(stmt.order_by(Message.created_at, Message.id)))
    membership.last_read_at = utcnow()
    db.commit()
    conversation = db.get(Conversation, conversation_id)
    return {"messages": hydrate_messages(db, messages, user_id),
            "conversation": hydrate_conversations(db, [conversation], user_id)[0]}


def send_message(db: Session, user, conversation_id: str, body: str, attachment: dict | None = None) -> dict:
    _membership(db, user.id, conversation_id)
    attachment = attachment or {}
    body = clean(body, 4000)
    file_id = attachment.get("file_id", "")
    if not body and not file_id:
        raise bad_request("Message cannot be empty.")
    others = list(db.scalars(select(ConversationMember.user_id).where(
        ConversationMember.conversation_id == conversation_id, ConversationMember.user_id != user.id)))
    if set(others) & network_service.blocked_user_ids(db, user.id):
        raise forbidden("Unable to send message.", "BLOCKED")
    if file_id:
        media_service.owned_file(db, user.id, file_id, ("Documents", "Post Media"))
    reply_to = attachment.get("reply_to", "")
    if reply_to:
        replied = db.get(Message, reply_to)
        if replied is None or replied.conversation_id != conversation_id:
            raise not_found("Message not found.")
    row = Message(conversation_id=conversation_id, sender_id=user.id, body=body,
                  attachment_file_id=file_id, attachment_type=attachment.get("type", ""), reply_to=reply_to)
    db.add(row)
    db.flush()
    conversation = db.get(Conversation, conversation_id)
    conversation.last_message_at = row.created_at
    events.publish(events.MESSAGE_SENT, db, sender=user, conversation_id=conversation_id,
                   recipient_ids=others, title=conversation.title if conversation.type == "group" else user.full_name,
                   preview=body[:120])
    db.commit()
    out = hydrate_messages(db, [row], user.id)[0]
    return {key: value for key, value in out.items() if key not in ("deleted", "replyTo", "status")}


def delete_message(db: Session, user, message_id: str) -> None:
    message = db.get(Message, message_id)
    if message is None:
        raise not_found("Message not found.")
    if message.sender_id != user.id and not is_staff(user.role):
        raise forbidden("Not allowed.")
    message.deleted, message.body = True, ""
    db.commit()


def react_message(db: Session, user, message_id: str, kind: str) -> tuple[dict, str]:
    message = db.get(Message, message_id)
    if message is None:
        raise not_found("Message not found.")
    _membership(db, user.id, message.conversation_id, "Not allowed.")
    kind = kind if kind in ("like", "love", "laugh", "wow", "sad") else "like"
    reaction = db.scalar(select(MessageReaction).where(
        MessageReaction.message_id == message_id, MessageReaction.user_id == user.id))
    removed = reaction is not None and reaction.type == kind
    if removed:
        db.delete(reaction)
        text = "Reaction removed."
    elif reaction:
        reaction.type = kind
        text = "Reaction updated."
    else:
        db.add(MessageReaction(message_id=message_id, user_id=user.id, type=kind))
        text = "Reaction added."
    db.commit()
    return {"removed": removed}, text


def search_messages(db: Session, user_id: str, conversation_id: str, query: str) -> list[dict]:
    _membership(db, user_id, conversation_id, "Not allowed.")
    query = clean(query, 100)
    if not query:
        return []
    rows = db.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.deleted.is_(False),
        Message.body.icontains(query, autoescape=True)).order_by(Message.created_at.desc()).limit(50))
    return [{"id": row.id, "body": row.body, "senderId": row.sender_id,
             "createdAt": row.created_at, "timeAgo": time_ago(row.created_at)} for row in rows]


def set_settings(db: Session, user_id: str, conversation_id: str, changes: dict) -> None:
    membership = _membership(db, user_id, conversation_id, "Not allowed.")
    for key in ("pinned", "muted"):
        if changes.get(key) is not None:
            setattr(membership, key, changes[key])
    db.commit()
