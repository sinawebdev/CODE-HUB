"""Business rules for identity. Other modules may import from here, never from models.py."""
import logging
import re
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import events
from app.core.config import settings
from app.core.email import EmailError, send_password_reset_code, send_verification_code, send_welcome
from app.core.errors import AppError, bad_request, conflict, forbidden, unauthorized
from app.core.roles import ACTIVE, ADMIN_ROLES, ALL_ROLES, EMPLOYER, PROFESSIONAL
from app.core.security import (
    create_access_token, generate_otp, hash_otp, hash_password, hash_token, new_opaque_token,
    otp_matches, verify_password,
)
from app.core.utils import as_utc, clean, utcnow
from app.modules.identity.models import RefreshToken, User, VerificationCode
from app.modules.platform import service as platform_service

logger = logging.getLogger("app.identity")

EMAIL_VERIFY = "email_verify"
PASSWORD_RESET = "password_reset"
MIN_PASSWORD = 8
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")
RESET_SENT = "If that email exists, a reset code has been sent."


# ---------------------------------------------------------------- lookups for other modules

def get_user(db: Session, user_id: str | None) -> User | None:
    return db.get(User, user_id) if user_id else None


def get_users(db: Session, user_ids) -> dict[str, User]:
    ids = {i for i in user_ids if i}
    if not ids:
        return {}
    return {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))}


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == clean(email).lower()))


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL.match(clean(email)))


def safe_user(user: User, include_contact: bool = False) -> dict:
    """Public shape of a user, exactly as the demo's safeUser_ returned it."""
    out = {
        "UserID": user.id, "FirstName": user.first_name, "LastName": user.last_name,
        "FullName": user.full_name, "Role": user.role, "Status": user.status, "City": user.city,
        "ProfessionalTitle": user.professional_title, "Verified": user.verified,
        "EmailVerified": user.email_verified, "CreatedAt": user.created_at,
    }
    if include_contact:
        out.update(Email=user.email, Phone=user.phone)
    return out


# ---------------------------------------------------------------- sessions (JWT + refresh tokens)

def _issue_session(db: Session, user: User, remember: bool, user_agent: str = "") -> dict:
    raw = new_opaque_token()
    lifetime = timedelta(days=settings.refresh_token_days) if remember else timedelta(hours=settings.session_hours)
    db.add(RefreshToken(
        user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + lifetime,
        remember=remember, user_agent=clean(user_agent, 250),
    ))
    access, expires_at = create_access_token(user.id, user.token_version)
    return {"accessToken": access, "refreshToken": raw, "expiresAt": expires_at}


def user_for_token(db: Session, claims: dict) -> User | None:
    """The active user behind a decoded access token, or None if it has been revoked."""
    user = db.get(User, claims.get("sub"))
    if user is None or user.status != ACTIVE or user.token_version != claims.get("ver"):
        return None
    return user


def refresh_session(db: Session, raw_token: str, user_agent: str = "") -> dict:
    """Swap a valid refresh token for a new access + refresh token pair (rotation)."""
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token or "")))
    if record is None or record.revoked_at is not None or as_utc(record.expires_at) < utcnow():
        raise unauthorized()
    user = db.get(User, record.user_id)
    if user is None or user.status != ACTIVE:
        raise unauthorized()
    record.revoked_at = utcnow()
    session = _issue_session(db, user, record.remember, user_agent or record.user_agent)
    db.commit()
    return {**session, "user": safe_user(user, True), "emailVerified": user.email_verified}


def logout(db: Session, raw_token: str | None) -> None:
    if raw_token:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
        db.commit()


def revoke_all_sessions(db: Session, user: User) -> None:
    """Sign the user out everywhere: kill refresh tokens and invalidate access tokens. Caller commits."""
    user.token_version = (user.token_version or 0) + 1
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


# ---------------------------------------------------------------- one-time codes

def _issue_code(db: Session, user: User, purpose: str) -> str:
    """Create (or replace) the user's code for `purpose`, enforcing the hourly request limit."""
    now = utcnow()
    record = db.scalar(select(VerificationCode).where(
        VerificationCode.user_id == user.id, VerificationCode.purpose == purpose))
    if record is None:
        record = VerificationCode(user_id=user.id, purpose=purpose, window_count=0)
        db.add(record)
    window_start, count = as_utc(record.window_started_at), record.window_count or 0
    if window_start is None or now - window_start > timedelta(hours=1):
        window_start, count = now, 0
    if count + 1 > settings.otp_max_requests_per_hour:
        raise AppError(429, "RATE_LIMITED", "Too many requests. Please try again later.")
    code = generate_otp()
    record.code_hash = hash_otp(code, user.id, purpose)
    record.expires_at = now + timedelta(minutes=settings.otp_expiry_minutes)
    record.attempts, record.sent_at = 0, now
    record.window_started_at, record.window_count = window_start, count + 1
    db.flush()
    return code


def _check_code(db: Session, user: User, purpose: str, code: str) -> VerificationCode:
    """Validate a submitted code; wrong guesses are counted (and committed) before raising."""
    code = re.sub(r"\s+", "", code or "")
    if not re.fullmatch(r"\d{6}", code):
        raise bad_request("Enter the 6-digit code.")
    record = db.scalar(select(VerificationCode).where(
        VerificationCode.user_id == user.id, VerificationCode.purpose == purpose))
    if record is None or not record.code_hash or record.expires_at is None:
        raise bad_request("No active code. Please request a new one.", "NO_OTP")
    if as_utc(record.expires_at) < utcnow():
        raise bad_request("This code has expired. Please request a new one.", "OTP_EXPIRED")
    if record.attempts >= settings.otp_max_attempts:
        raise bad_request("Too many attempts. Please request a new code.", "OTP_ATTEMPTS_EXCEEDED")
    if not otp_matches(code, user.id, purpose, record.code_hash):
        record.attempts += 1
        db.commit()
        left = settings.otp_max_attempts - record.attempts
        suffix = f" {left} attempt{'' if left == 1 else 's'} left." if left > 0 else ""
        raise bad_request(f"Incorrect code.{suffix}", "OTP_INVALID")
    return record


def _send_verification(user: User, code: str) -> None:
    send_verification_code(user.email, user.first_name, code, settings.otp_expiry_minutes)


# ---------------------------------------------------------------- registration & login

def register(db: Session, data, user_agent: str = "") -> dict:
    """`data` is a RegisterIn schema (validated names, email format and password length)."""
    role = data.role if data.role in ALL_ROLES and data.role not in ADMIN_ROLES else PROFESSIONAL
    platform_service.assert_registration_open(db, role)
    if data.password != data.confirm_password:
        raise bad_request("Passwords do not match.")
    email = data.email.lower()
    if find_user_by_email(db, email):
        raise conflict("An account with this email already exists.", "DUPLICATE_EMAIL")
    city = data.city or platform_service.get_setting(db, "defaultCity")
    user = User(
        first_name=data.first_name, last_name=data.last_name, email=email, phone=data.phone,
        password_hash=hash_password(data.password), role=role, status=ACTIVE, city=city,
        professional_title=data.professional_title, verified=False, email_verified=False,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise conflict("An account with this email already exists.", "DUPLICATE_EMAIL") from None
    events.publish(events.USER_REGISTERED, db, user=user)
    session = _issue_session(db, user, remember=False, user_agent=user_agent)
    code = None
    try:
        code = _issue_code(db, user, EMAIL_VERIFY)
    except AppError:
        logger.warning("Could not issue verification code at registration", extra={"user_id": user.id})
    platform_service.audit(db, user.id, "REGISTER", "User", user.id, email)
    db.commit()
    if code:
        try:
            _send_verification(user, code)
        except EmailError:
            logger.error("Verification email failed at registration", extra={"user_id": user.id})
    return {**session, "user": safe_user(user, True), "emailVerified": False, "email": email}


def login(db: Session, email: str, password: str, remember: bool, user_agent: str = "") -> tuple[dict, str]:
    email = clean(email).lower()
    if not is_valid_email(email) or not password:
        raise bad_request("Enter your email and password.")
    user = find_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)  # same timing as a real check
        raise unauthorized("Invalid email or password.", "INVALID_CREDENTIALS")
    if user.locked_until and as_utc(user.locked_until) > utcnow():
        raise AppError(423, "ACCOUNT_LOCKED", "Account temporarily locked. Try again later.")
    if user.status == "Suspended":
        raise forbidden("This account has been suspended.", "ACCOUNT_SUSPENDED")
    if user.status == "Disabled":
        raise forbidden("This account is disabled.", "ACCOUNT_DISABLED")
    if user.status != ACTIVE:
        raise forbidden("This account is pending approval.", "ACCOUNT_PENDING")
    platform_service.assert_not_in_maintenance(db, user.role)
    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = utcnow() + timedelta(minutes=settings.lock_minutes)
            user.failed_attempts = 0
        logger.warning("Failed login attempt", extra={"user_id": user.id})
        db.commit()
        raise unauthorized("Invalid email or password.", "INVALID_CREDENTIALS")
    user.last_login, user.failed_attempts, user.locked_until = utcnow(), 0, None
    session = _issue_session(db, user, remember, user_agent)
    platform_service.audit(db, user.id, "LOGIN", "User", user.id)
    db.commit()
    message = "Welcome back." if user.email_verified else "Please verify your email to continue."
    return {**session, "user": safe_user(user, True), "emailVerified": user.email_verified}, message


# ---------------------------------------------------------------- email verification

def verify_email(db: Session, user: User, code: str) -> tuple[dict, str]:
    if user.email_verified:
        return {"emailVerified": True, "user": safe_user(user, True)}, "Email already verified."
    record = _check_code(db, user, EMAIL_VERIFY, code)
    db.delete(record)
    user.email_verified = True
    events.publish(events.EMAIL_VERIFIED, db, user=user)
    platform_service.audit(db, user.id, "EMAIL_VERIFIED", "User", user.id)
    db.commit()
    if platform_service.is_enabled(db, "emailNotifications"):
        try:
            send_welcome(user.email, user.first_name)
        except EmailError:
            logger.warning("Welcome email failed", extra={"user_id": user.id})
    return {"emailVerified": True, "user": safe_user(user, True)}, "Email verified successfully."


def resend_verification(db: Session, user: User) -> str:
    if user.email_verified:
        return "Email already verified."
    record = db.scalar(select(VerificationCode).where(
        VerificationCode.user_id == user.id, VerificationCode.purpose == EMAIL_VERIFY))
    if record is not None and record.sent_at is not None:
        elapsed = (utcnow() - as_utc(record.sent_at)).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            wait = int(settings.otp_resend_cooldown_seconds - elapsed) + 1
            raise AppError(429, "RESEND_COOLDOWN", f"Please wait {wait}s before requesting a new code.")
    code = _issue_code(db, user, EMAIL_VERIFY)
    platform_service.audit(db, user.id, "OTP_RESEND", "User", user.id)
    db.commit()
    _deliver(lambda: _send_verification(user, code))
    return "A new code has been sent."


def change_unverified_email(db: Session, user: User, new_email: str) -> str:
    if user.email_verified:
        raise conflict("Your email is already verified.", "ALREADY_VERIFIED")
    new_email = clean(new_email).lower()
    if not is_valid_email(new_email):
        raise bad_request("Enter a valid email address.")
    _assert_email_free(db, new_email, user.id)
    user.email = new_email
    code = _issue_code(db, user, EMAIL_VERIFY)
    platform_service.audit(db, user.id, "EMAIL_CHANGE_PENDING", "User", user.id, new_email)
    db.commit()
    _deliver(lambda: _send_verification(user, code))
    return new_email


def _assert_email_free(db: Session, email: str, user_id: str) -> None:
    other = find_user_by_email(db, email)
    if other is not None and other.id != user_id:
        raise conflict("That email is already in use.", "DUPLICATE_EMAIL")


def _deliver(send) -> None:
    try:
        send()
    except EmailError:
        raise AppError(502, "EMAIL_SEND_FAILED", "We could not send the email. Please try again.") from None


# ---------------------------------------------------------------- passwords

def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise unauthorized("Current password is incorrect.", "INVALID_CREDENTIALS")
    if len(new_password or "") < MIN_PASSWORD:
        raise bad_request("New password must be at least 8 characters.")
    user.password_hash = hash_password(new_password)
    revoke_all_sessions(db, user)
    platform_service.audit(db, user.id, "PASSWORD_CHANGE", "User", user.id)
    db.commit()


def request_password_reset(db: Session, email: str) -> None:
    """Email a reset code. Always looks the same to the caller so accounts cannot be probed."""
    user = find_user_by_email(db, email) if is_valid_email(email) else None
    if user is None or user.status != ACTIVE:
        return
    try:
        code = _issue_code(db, user, PASSWORD_RESET)
    except AppError:
        return  # rate limited: stay silent
    platform_service.audit(db, user.id, "PASSWORD_RESET_REQUESTED", "User", user.id)
    db.commit()
    try:
        send_password_reset_code(user.email, user.first_name, code, settings.otp_expiry_minutes)
    except EmailError:
        logger.error("Password reset email failed", extra={"user_id": user.id})


def confirm_password_reset(db: Session, email: str, code: str, new_password: str) -> None:
    if len(new_password or "") < MIN_PASSWORD:
        raise bad_request("New password must be at least 8 characters.")
    user = find_user_by_email(db, email) if is_valid_email(email) else None
    if user is None or user.status != ACTIVE:
        raise bad_request("This code is invalid or has expired.", "OTP_INVALID")
    record = _check_code(db, user, PASSWORD_RESET, code)
    db.delete(record)
    user.password_hash = hash_password(new_password)
    user.failed_attempts, user.locked_until = 0, None
    revoke_all_sessions(db, user)
    platform_service.audit(db, user.id, "PASSWORD_RESET", "User", user.id)
    db.commit()


# ---------------------------------------------------------------- account fields edited from the profile page

def update_account(db: Session, user: User, changes: dict) -> None:
    """Apply firstName/lastName/phone/city/professionalTitle/email edits. Caller commits."""
    for key, attr, limit in (("first_name", "first_name", 100), ("last_name", "last_name", 100),
                             ("phone", "phone", 40), ("city", "city", 100),
                             ("professional_title", "professional_title", 160)):
        if changes.get(key) is not None:
            setattr(user, attr, clean(changes[key], limit))
    new_email = clean(changes.get("email")).lower()
    if new_email and new_email != user.email:
        if not is_valid_email(new_email):
            raise bad_request("Invalid email address.")
        _assert_email_free(db, new_email, user.id)
        user.email, user.email_verified = new_email, False  # a new address must be verified again


def promote_to_employer(db: Session, user: User) -> None:
    """Creating a company page turns members into employers. Caller commits."""
    if user.role in (PROFESSIONAL, "Normal User", "Student"):
        user.role = EMPLOYER
