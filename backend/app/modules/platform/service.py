"""Business rules for platform settings and the audit log. Other modules may import from here, never from models.py."""
import json
import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.roles import EMPLOYER, is_staff
from app.core.utils import clean
from app.modules.platform.models import AuditLog, PlatformSetting

DEFAULTS: dict[str, str] = {
    "platformName": settings.app_name,
    "logoFileId": "",
    "primaryColor": "#0E7C4A",
    "secondaryColor": "#F2B705",
    "registrationEnabled": "TRUE",
    "employerRegistration": "TRUE",
    "emailNotifications": "TRUE",
    "maintenanceMode": "FALSE",
    "defaultCity": "Koforidua",
    "defaultRegion": "Eastern Region",
    "defaultCountry": "Ghana",
}
BOOLEAN_KEYS = ("registrationEnabled", "employerRegistration", "emailNotifications", "maintenanceMode")
ADMIN_KEYS = (
    "platformName", "logoFileId", "primaryColor", "secondaryColor", "registrationEnabled",
    "employerRegistration", "emailNotifications", "maintenanceMode", "defaultCity", "defaultRegion",
)
PUBLIC_KEYS = (
    "platformName", "primaryColor", "secondaryColor", "registrationEnabled",
    "employerRegistration", "maintenanceMode", "defaultCity", "defaultRegion",
)
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def get_settings(db: Session, keys: tuple[str, ...] | None = None) -> dict[str, str]:
    values = dict(DEFAULTS)
    values.update({row.key: row.value for row in db.scalars(select(PlatformSetting))})
    return {key: values.get(key, "") for key in keys} if keys else values


def get_setting(db: Session, key: str) -> str:
    row = db.get(PlatformSetting, key)
    return row.value if row is not None else DEFAULTS.get(key, "")


def is_enabled(db: Session, key: str) -> bool:
    return get_setting(db, key) == "TRUE"


def _put(db: Session, key: str, value: str) -> None:
    row = db.get(PlatformSetting, key)
    if row is None:
        db.add(PlatformSetting(key=key, value=value))
    else:
        row.value = value


def save_settings(db: Session, actor_id: str, changes: dict[str, object]) -> dict[str, str]:
    """Admin settings form. Booleans are stored as 'TRUE'/'FALSE'; invalid colours are ignored."""
    for key in ADMIN_KEYS:
        if key not in changes or changes[key] is None:
            continue
        value = clean(changes[key], 500)
        if key in BOOLEAN_KEYS:
            value = "TRUE" if value.lower() in ("true", "1", "on") else "FALSE"
        elif key in ("primaryColor", "secondaryColor") and not _COLOR.match(value):
            continue
        _put(db, key, value)
    audit(db, actor_id, "UPDATE_SETTINGS", "Settings", "", json.dumps(changes, default=str)[:500])
    db.commit()
    return get_settings(db, ADMIN_KEYS)


def ensure_defaults(db: Session) -> list[str]:
    """Insert any missing default settings (used by the setup command). Returns the keys added."""
    existing = set(db.scalars(select(PlatformSetting.key)))
    added = [key for key in DEFAULTS if key not in existing]
    for key in added:
        db.add(PlatformSetting(key=key, value=DEFAULTS[key]))
    db.commit()
    return added


def assert_not_in_maintenance(db: Session, role: str | None) -> None:
    if is_staff(role) or not is_enabled(db, "maintenanceMode"):
        return
    raise AppError(503, "MAINTENANCE", "The platform is under maintenance.")


def assert_registration_open(db: Session, role: str) -> None:
    if not is_enabled(db, "registrationEnabled"):
        raise AppError(403, "REGISTRATION_DISABLED", "Registration is currently disabled.")
    if role == EMPLOYER and not is_enabled(db, "employerRegistration"):
        raise AppError(403, "EMPLOYER_REGISTRATION_DISABLED", "Employer registration is currently disabled.")


def audit(db: Session, actor_id: str | None, action: str, target_type: str = "",
          target_id: str | None = "", details: object = "") -> None:
    """Record an action. Joins the caller's transaction; the caller commits."""
    db.add(AuditLog(
        actor_id=actor_id or "", action=action, target_type=target_type or "",
        target_id=target_id or "", details=clean(details, 1000),
    ))


def list_audit_logs(db: Session, query: str = "", limit: int = 100) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 300))
    if query:
        stmt = stmt.where(or_(*(
            col.icontains(query, autoescape=True)
            for col in (AuditLog.id, AuditLog.actor_id, AuditLog.action, AuditLog.target_type,
                        AuditLog.target_id, AuditLog.details)
        )))
    return [
        {"LogID": row.id, "Timestamp": row.created_at, "ActorID": row.actor_id, "Action": row.action,
         "TargetType": row.target_type, "TargetID": row.target_id, "Details": row.details}
        for row in db.scalars(stmt)
    ]
