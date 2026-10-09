"""Password hashing (Argon2), JWT access tokens, refresh tokens, one-time codes and signed links."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.errors import unauthorized
from app.core.utils import utcnow

ALGORITHM = "HS256"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: str, token_version: int) -> tuple[str, datetime]:
    """Short-lived JWT. `ver` lets a password change invalidate every outstanding token."""
    expires_at = utcnow() + timedelta(minutes=settings.access_token_minutes)
    claims = {"sub": user_id, "ver": token_version, "type": "access", "iat": utcnow(), "exp": expires_at}
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM), expires_at


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise unauthorized("Your session has expired.", "TOKEN_EXPIRED") from None
    except jwt.PyJWTError:
        raise unauthorized() from None
    if claims.get("type") != "access" or not claims.get("sub"):
        raise unauthorized()
    return claims


def new_opaque_token() -> str:
    """Random refresh token handed to the client; only its hash is stored."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_otp(length: int = 6) -> str:
    return str(secrets.randbelow(10**length)).zfill(length)


def hash_otp(code: str, user_id: str, purpose: str) -> str:
    message = f"{purpose}:{user_id}:{code}".encode()
    return hmac.new(settings.secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def otp_matches(code: str, user_id: str, purpose: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(code, user_id, purpose), expected_hash or "")


def create_signed_token(subject: str, purpose: str, minutes: int = 60) -> str:
    """Short-lived token for links such as private media (CVs) shown to an authorised viewer."""
    expires_at = utcnow() + timedelta(minutes=minutes)
    claims = {"sub": subject, "type": purpose, "exp": expires_at}
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def verify_signed_token(token: str, subject: str, purpose: str) -> bool:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return False
    return claims.get("sub") == subject and claims.get("type") == purpose
