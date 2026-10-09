"""Business rules for network. Other modules may import from here, never from models.py."""
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.modules.network.models import Block, Connection, Follow
from app.core import events
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.utils import clean
from app.modules.identity import service as identity_service
from app.modules.identity import service_admin as users_admin
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service

ACCEPTED = "Accepted"
PENDING = "Pending"


# ================================================================ public interface (used by other modules)
# Keep these signatures stable: profiles, feed, messaging, search and the bootstrap endpoint call them.

def connection_between(db: Session, a: str | None, b: str | None) -> Connection | None:
    if not a or not b:
        return None
    return db.scalar(select(Connection).where(or_(
        and_(Connection.requester_id == a, Connection.addressee_id == b),
        and_(Connection.requester_id == b, Connection.addressee_id == a),
    )).limit(1))


def are_connected(db: Session, a: str | None, b: str | None) -> bool:
    conn = connection_between(db, a, b)
    return conn is not None and conn.status == ACCEPTED


def is_blocked(db: Session, a: str | None, b: str | None) -> bool:
    """True when either user has blocked the other."""
    if not a or not b:
        return False
    return db.scalar(select(Block.id).where(or_(
        and_(Block.user_id == a, Block.blocked_user_id == b),
        and_(Block.user_id == b, Block.blocked_user_id == a),
    )).limit(1)) is not None


def connected_user_ids(db: Session, user_id: str) -> set[str]:
    rows = db.execute(select(Connection.requester_id, Connection.addressee_id).where(
        Connection.status == ACCEPTED,
        or_(Connection.requester_id == user_id, Connection.addressee_id == user_id),
    ))
    return {addressee if requester == user_id else requester for requester, addressee in rows}


def blocked_user_ids(db: Session, user_id: str) -> set[str]:
    """Everyone this user blocked or was blocked by (hide them from each other)."""
    rows = db.execute(select(Block.user_id, Block.blocked_user_id).where(
        or_(Block.user_id == user_id, Block.blocked_user_id == user_id)))
    return {blocked if owner == user_id else owner for owner, blocked in rows}


def mutual_count(db: Session, a: str, b: str) -> int:
    return len(connected_user_ids(db, a) & connected_user_ids(db, b))


def mutual_counts(db: Session, user_id: str, other_ids) -> dict[str, int]:
    """Mutual-connection counts between user_id and each of other_ids, in two queries."""
    others = {i for i in other_ids if i}
    mine = connected_user_ids(db, user_id)
    counts = dict.fromkeys(others, 0)
    if not mine or not others:
        return counts
    rows = db.execute(select(Connection.requester_id, Connection.addressee_id).where(
        Connection.status == ACCEPTED,
        or_(and_(Connection.requester_id.in_(others), Connection.addressee_id.in_(mine)),
            and_(Connection.addressee_id.in_(others), Connection.requester_id.in_(mine))),
    ))
    for requester, addressee in rows:
        if requester in others and addressee in mine:
            counts[requester] += 1
        if addressee in others and requester in mine:
            counts[addressee] += 1
    return counts


def is_following(db: Session, follower_id: str | None, following_id: str | None) -> bool:
    if not follower_id or not following_id:
        return False
    return db.scalar(select(Follow.id).where(
        Follow.follower_id == follower_id, Follow.following_id == following_id).limit(1)) is not None


def relationship(db: Session, viewer_id: str, target_id: str) -> dict:
    """How the viewer relates to the target (profile page buttons)."""
    conn = connection_between(db, viewer_id, target_id)
    pending = conn is not None and conn.status == PENDING
    return {
        "connected": conn is not None and conn.status == ACCEPTED,
        "connectionId": conn.id if conn else "",
        "pendingOutgoing": pending and conn.requester_id == viewer_id,
        "pendingIncoming": pending and conn.addressee_id == viewer_id,
        "following": is_following(db, viewer_id, target_id),
        "blocked": is_blocked(db, viewer_id, target_id),
        "mutual": mutual_count(db, viewer_id, target_id),
    }


def network_stats(db: Session, user_id: str) -> dict:
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    return {
        "connections": len(connected_user_ids(db, user_id)),
        "followers": count(select(func.count()).select_from(Follow).where(Follow.following_id == user_id)),
        "following": count(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)),
    }


def pending_request_count(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Connection).where(
        Connection.addressee_id == user_id, Connection.status == PENDING)) or 0


# ================================================================ network features (connections, follows, blocks)

def _target(db: Session, target_id: str):
    target = identity_service.get_user(db, target_id)
    if target is None:
        raise not_found("User not found.")
    return target


def _accept(db: Session, user, connection: Connection) -> str:
    connection.status = ACCEPTED
    events.publish(events.CONNECTION_ACCEPTED, db, accepter=user,
                   requester_id=connection.requester_id, connection_id=connection.id)
    db.commit()
    return "Connection accepted."


def send_connection(db: Session, user, target_id: str, message: str = "") -> str:
    if target_id == user.id:
        raise bad_request("You cannot connect with yourself.")
    _target(db, target_id)
    if is_blocked(db, user.id, target_id):
        raise forbidden("Unable to send request.", "BLOCKED")
    existing = connection_between(db, user.id, target_id)
    if existing:
        if existing.status == ACCEPTED:
            raise conflict("You are already connected.")
        if existing.addressee_id == user.id:
            return _accept(db, user, existing)
        raise conflict("Connection request already pending.")
    row = Connection(requester_id=user.id, addressee_id=target_id, message=clean(message, 300))
    db.add(row)
    db.flush()
    events.publish(events.CONNECTION_REQUESTED, db, requester=user,
                   addressee_id=target_id, connection_id=row.id)
    db.commit()
    return "Connection request sent."


def respond_connection(db: Session, user, connection_id: str, action: str) -> str:
    row = db.get(Connection, connection_id)
    if row is None:
        raise not_found("Request not found.")
    if user.id not in (row.requester_id, row.addressee_id):
        raise forbidden("Not allowed.")
    if action == "accept":
        if row.addressee_id != user.id:
            raise forbidden("Not allowed.")
        if row.status != PENDING:
            raise bad_request("Request is no longer pending.")
        if is_blocked(db, user.id, row.requester_id):
            raise forbidden("Unable to send request.", "BLOCKED")
        return _accept(db, user, row)
    if action in ("reject", "cancel", "remove"):
        if action == "remove" and row.status != ACCEPTED:
            raise bad_request("Not connected.")
        db.delete(row)
        db.commit()
        return "Connection removed." if action == "remove" else "Request removed."
    raise bad_request("Unknown action.")


def _person(card: dict) -> dict:
    return {key: card[key] for key in ("userId", "name", "headline", "photo")}


def list_connections(db: Session, viewer_id: str, target_id: str | None = None) -> list[dict]:
    target_id = target_id or viewer_id
    rows = list(db.scalars(select(Connection).where(Connection.status == ACCEPTED,
        or_(Connection.requester_id == target_id, Connection.addressee_id == target_id))))
    ids = {row.id: row.addressee_id if row.requester_id == target_id else row.requester_id for row in rows}
    cards = profiles_service.user_cards(db, ids.values())
    hidden = blocked_user_ids(db, viewer_id)
    return [{**_person(cards[uid]), "connectionId": row.id,
             "verified": cards[uid]["verified"], "city": cards[uid]["city"]}
            for row in rows if (uid := ids[row.id]) in cards and uid not in hidden]


def list_requests(db: Session, user_id: str) -> dict:
    rows = list(db.scalars(select(Connection).where(Connection.status == PENDING,
        or_(Connection.requester_id == user_id, Connection.addressee_id == user_id))))
    ids = {row.id: row.addressee_id if row.requester_id == user_id else row.requester_id for row in rows}
    cards = profiles_service.user_cards(db, ids.values())
    mutual = mutual_counts(db, user_id, ids.values())
    hidden = blocked_user_ids(db, user_id)
    out = {"incoming": [], "outgoing": []}
    for row in rows:
        uid = ids[row.id]
        if uid not in cards or uid in hidden:
            continue
        item = {**_person(cards[uid]), "connectionId": row.id, "createdAt": row.created_at}
        incoming = row.addressee_id == user_id
        if incoming:
            item.update(message=row.message, mutual=mutual[uid])
        out["incoming" if incoming else "outgoing"].append(item)
    return out


def suggestions(db: Session, user, limit: int = 12) -> list[dict]:
    rows = db.execute(select(Connection.requester_id, Connection.addressee_id).where(
        or_(Connection.requester_id == user.id, Connection.addressee_id == user.id)))
    excluded = {user.id} | blocked_user_ids(db, user.id)
    excluded.update(b if a == user.id else a for a, b in rows)
    candidates = users_admin.list_active_users(db, exclude_ids=excluded)
    cards = profiles_service.user_cards(db, [u.id for u in candidates])
    skills = profiles_service.skill_map(db, [user.id] + [u.id for u in candidates])
    mutual = mutual_counts(db, user.id, cards)
    region = platform_service.get_setting(db, "defaultRegion")
    out = []
    for candidate in candidates:
        card = cards[candidate.id]
        score = 3 if user.city and candidate.city.lower() == user.city.lower() else 0
        score += int(card.get("region", "") == region)
        score += min(len(skills[user.id] & skills[candidate.id]), 5) + mutual[candidate.id] * 2
        out.append({**_person(card), "city": card["city"], "verified": card["verified"],
                    "mutual": mutual[candidate.id], "score": score})
    return sorted(out, key=lambda card: -card["score"])[:limit]


def follow(db: Session, user, target_id: str, enabled: bool) -> str:
    if target_id == user.id:
        raise bad_request("You cannot follow yourself.")
    _target(db, target_id)
    if is_blocked(db, user.id, target_id):
        raise forbidden("Unable to follow this user.", "BLOCKED")
    row = db.scalar(select(Follow).where(Follow.follower_id == user.id, Follow.following_id == target_id))
    if not enabled:
        if row:
            db.delete(row)
        db.commit()
        return "Unfollowed."
    if row:
        return "Already following."
    db.add(Follow(follower_id=user.id, following_id=target_id))
    events.publish(events.USER_FOLLOWED, db, follower=user, following_id=target_id)
    db.commit()
    return "Now following."


def followers(db: Session, viewer_id: str, target_id: str | None, mode: str) -> list[dict]:
    target_id = target_id or viewer_id
    following = mode == "following"
    ids = list(db.scalars(select(Follow.following_id if following else Follow.follower_id).where(
        Follow.follower_id == target_id if following else Follow.following_id == target_id)))
    hidden = blocked_user_ids(db, viewer_id)
    cards = profiles_service.user_cards(db, ids)
    return [_person(cards[uid]) for uid in ids if uid in cards and uid not in hidden]


def block(db: Session, user, target_id: str, enabled: bool) -> str:
    if target_id == user.id:
        raise bad_request("Invalid operation.")
    _target(db, target_id)
    row = db.scalar(select(Block).where(Block.user_id == user.id, Block.blocked_user_id == target_id))
    if not enabled:
        if row:
            db.delete(row)
        db.commit()
        return "User unblocked."
    if row:
        return "Already blocked."
    db.add(Block(user_id=user.id, blocked_user_id=target_id))
    db.execute(delete(Connection).where(or_(
        and_(Connection.requester_id == user.id, Connection.addressee_id == target_id),
        and_(Connection.requester_id == target_id, Connection.addressee_id == user.id))))
    db.execute(delete(Follow).where(or_(
        and_(Follow.follower_id == user.id, Follow.following_id == target_id),
        and_(Follow.follower_id == target_id, Follow.following_id == user.id))))
    db.commit()
    return "User blocked."


def list_blocks(db: Session, user_id: str) -> list[dict]:
    ids = list(db.scalars(select(Block.blocked_user_id).where(Block.user_id == user_id)))
    cards = profiles_service.user_cards(db, ids)
    return [{key: cards[uid][key] for key in ("userId", "name")} for uid in ids if uid in cards]
