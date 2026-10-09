"""User administration for identity: roles, statuses, badges, stats, admin lists and CLI helpers."""
from datetime import timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, forbidden, not_found
from app.core.roles import ACTIVE, ADMIN_ROLES, ALL_ROLES, SUPER_ADMIN, USER_STATUSES
from app.core.security import hash_password
from app.core.utils import clean, utcnow
from app.modules.identity.models import RefreshToken, User, VerificationCode
from app.modules.identity.service import get_user, revoke_all_sessions, safe_user
from app.modules.platform import service as platform_service


def set_user_status(db: Session, actor: User, user_id: str, status: str) -> None:
    if status not in USER_STATUSES:
        raise bad_request("Invalid user status.")
    user = get_user(db, user_id)
    if user is None:
        raise not_found("User not found.")
    if user.role == SUPER_ADMIN and actor.role != SUPER_ADMIN:
        raise forbidden("Only a Super Admin can modify a Super Admin.")
    if user.id == actor.id and status != ACTIVE:
        raise forbidden("You cannot change your own status.")
    user.status = status
    if status != ACTIVE:
        revoke_all_sessions(db, user)
    platform_service.audit(db, actor.id, "SET_USER_STATUS", "User", user.id, status)
    db.commit()


def set_user_role(db: Session, actor: User, user_id: str, role: str) -> None:
    if role not in ALL_ROLES:
        raise bad_request("Invalid role.")
    user = get_user(db, user_id)
    if user is None:
        raise not_found("User not found.")
    if role == SUPER_ADMIN and actor.role != SUPER_ADMIN:
        raise forbidden("Only a Super Admin can assign Super Admin.")
    if user.role == SUPER_ADMIN and actor.role != SUPER_ADMIN:
        raise forbidden("Only a Super Admin can modify a Super Admin.")
    if user.id == actor.id and actor.role == SUPER_ADMIN and role != SUPER_ADMIN:
        remaining = db.scalar(select(func.count()).select_from(User).where(
            User.role == SUPER_ADMIN, User.status == ACTIVE))
        if remaining <= 1:
            raise forbidden("You are the last Super Admin. Promote another user first.")
    user.role = role
    platform_service.audit(db, actor.id, "SET_USER_ROLE", "User", user.id, role)
    db.commit()


def set_verified(db: Session, user_id: str, verified: bool) -> None:
    """Verified badge on a profile (granted through the admin verification centre). Caller commits."""
    user = get_user(db, user_id)
    if user is not None:
        user.verified = verified


def admin_user_detail(user: User) -> dict:
    out = safe_user(user, include_contact=True)
    out.update(LastLogin=user.last_login, FailedAttempts=user.failed_attempts or 0,
               LockedUntil=user.locked_until, EmailVerified=user.email_verified)
    return out


def admin_row(user: User) -> dict:
    """A user as a raw admin-table row (sheet-style keys, secrets removed)."""
    return {
        "UserID": user.id, "FirstName": user.first_name, "LastName": user.last_name,
        "Email": user.email, "Phone": user.phone, "Role": user.role, "Status": user.status,
        "City": user.city, "ProfessionalTitle": user.professional_title, "Verified": user.verified,
        "CreatedAt": user.created_at, "UpdatedAt": user.updated_at, "LastLogin": user.last_login,
        "FailedAttempts": user.failed_attempts or 0, "LockedUntil": user.locked_until,
        "EmailVerified": user.email_verified,
    }


def list_users_admin(db: Session, query: str = "", status: str = "", limit: int = 100) -> list[dict]:
    stmt = select(User).order_by(User.created_at.desc()).limit(min(max(limit, 1), 300))
    if status:
        stmt = stmt.where(User.status == status)
    if query:
        stmt = stmt.where(or_(*(
            col.icontains(query, autoescape=True)
            for col in (User.id, User.first_name, User.last_name, User.email, User.city,
                        User.role, User.status, User.professional_title)
        )))
    return [admin_row(u) for u in db.scalars(stmt)]


def search_users(db: Session, query: str, limit: int = 12, exclude_ids=()) -> list[User]:
    """Active users whose name, title or city contains `query`."""
    stmt = select(User).where(User.status == ACTIVE, or_(
        User.first_name.icontains(query, autoescape=True),
        User.last_name.icontains(query, autoescape=True),
        (User.first_name + " " + User.last_name).icontains(query, autoescape=True),
        User.professional_title.icontains(query, autoescape=True),
        User.city.icontains(query, autoescape=True),
    ))
    if exclude_ids:
        stmt = stmt.where(User.id.not_in(list(exclude_ids)))
    return list(db.scalars(stmt.order_by(User.created_at.desc()).limit(limit)))


def list_active_users(db: Session, exclude_ids=(), limit: int = 500) -> list[User]:
    """Candidate pool for people suggestions."""
    stmt = select(User).where(User.status == ACTIVE)
    if exclude_ids:
        stmt = stmt.where(User.id.not_in(list(exclude_ids)))
    return list(db.scalars(stmt.order_by(User.created_at.desc()).limit(limit)))


def user_stats(db: Session) -> dict:
    """User numbers for the admin dashboard."""
    since = utcnow() - timedelta(days=30)
    count = lambda *where: db.scalar(select(func.count()).select_from(User).where(*where)) or 0  # noqa: E731
    roles = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    today = utcnow().date()
    created = [c.date() for c in db.scalars(
        select(User.created_at).where(User.created_at >= utcnow() - timedelta(days=8)))]
    trend = []
    for back in range(6, -1, -1):
        day = today - timedelta(days=back)
        trend.append({"label": day.strftime("%m-%d"), "value": sum(1 for c in created if c == day)})
    return {
        "totalUsers": count(),
        "activeUsers": count(User.last_login >= since),
        "newUsers": count(User.created_at >= since),
        "unverifiedEmails": count(User.email_verified.is_(False)),
        "signupTrend": trend,
        "roleBreakdown": [{"label": r, "value": roles.get(r, 0)} for r in ALL_ROLES],
    }


# ---------------------------------------------------------------- command-line helpers (app/cli.py)

def create_admin(db: Session, email: str, password: str, first_name: str = "KoforLink",
                 last_name: str = "Administrator") -> User:
    user = User(
        first_name=first_name, last_name=last_name, email=clean(email).lower(),
        password_hash=hash_password(password), role=SUPER_ADMIN, status=ACTIVE,
        city=platform_service.get_setting(db, "defaultCity"), professional_title="Platform Administrator",
        verified=True, email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def reset_password(db: Session, user: User, password: str) -> None:
    user.password_hash = hash_password(password)
    user.email_verified, user.failed_attempts, user.locked_until = True, 0, None
    revoke_all_sessions(db, user)
    db.commit()


def list_admins(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role.in_(ADMIN_ROLES)).order_by(User.created_at)))


def purge_expired_sessions(db: Session, older_than_days: int = 90) -> int:
    """Delete refresh tokens that expired more than `older_than_days` ago and stale one-time codes."""
    cutoff = utcnow() - timedelta(days=older_than_days)
    removed = db.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff)).rowcount or 0
    removed += db.execute(delete(VerificationCode).where(
        VerificationCode.expires_at < utcnow() - timedelta(days=1))).rowcount or 0
    db.commit()
    return removed
