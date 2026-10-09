"""Small pure helpers shared by every module (ids, time, text, geo)."""
import math
import re
import secrets
from datetime import UTC, date, datetime

_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)
_BAD_SCHEME = re.compile(r"^(javascript|data|vbscript|file|blob):", re.IGNORECASE)


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    """Readable, unguessable primary keys such as USR-3f9a2c1b9d4e7a60."""
    return f"{prefix}-{secrets.token_hex(8)}"


def clean(value: object, max_len: int | None = None) -> str:
    """Trim a user-supplied value and cap its length."""
    text = "" if value is None else str(value).strip()
    return text[:max_len] if max_len is not None else text


def safe_url(value: object) -> str:
    """Only allow plain http(s) links; anything else becomes an empty string."""
    text = clean(value)
    if not text or _BAD_SCHEME.match(text) or not _URL_SCHEME.match(text):
        return ""
    return text[:500]


def slugify(value: str) -> str:
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", clean(value).lower()))


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def is_past(value: datetime | date | None) -> bool:
    if value is None:
        return False
    if isinstance(value, datetime):
        return as_utc(value) < utcnow()
    return value < utcnow().date()


def time_ago(value: datetime | None) -> str:
    """Compact relative time used across the UI: just now, 5m, 3h, 2d, 1w, 4mo, 2y."""
    if value is None:
        return ""
    secs = int((utcnow() - as_utc(value)).total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}h"
    days = hrs // 24
    if days < 7:
        return f"{days}d"
    if days // 7 < 5:
        return f"{days // 7}w"
    if days // 30 < 12:
        return f"{days // 30}mo"
    return f"{days // 365}y"


def haversine_km(lat1, lon1, lat2, lon2) -> float | None:
    """Great-circle distance in km, or None when any coordinate is missing."""
    try:
        lat1, lon1, lat2, lon2 = (float(v) for v in (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return None
    rad = math.radians
    d_lat, d_lon = rad(lat2 - lat1), rad(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(d_lon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def to_float(value: object) -> float | None:
    """Parse an optional number; blank or invalid input becomes None (never 0)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
