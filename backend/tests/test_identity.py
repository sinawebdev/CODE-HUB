import re
from datetime import timedelta

from app.core.utils import utcnow
from tests.conftest import PASSWORD, set_setting

REGISTER = {
    "firstName": "Ama", "lastName": "Mensah", "email": "Ama@Example.com", "phone": "+233 20 000 0000",
    "password": "secret-pass", "confirmPassword": "secret-pass", "city": "Koforidua",
    "professionalTitle": "Software Engineer", "role": "Professional",
}


def _code(outbox) -> str:
    return re.search(r"\b(\d{6})\b", outbox[-1]["text"]).group(1)


def _register(client, **overrides):
    return client.post("/api/v1/auth/register", json={**REGISTER, **overrides})


def test_register_creates_unverified_user_profile_and_sends_code(client, outbox):
    response = _register(client)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["user"]["Email"] == "ama@example.com" and data["emailVerified"] is False
    assert data["accessToken"] and data["refreshToken"]
    assert outbox and outbox[-1]["to"] == "ama@example.com" and _code(outbox)
    headers = {"Authorization": f"Bearer {data['accessToken']}"}
    # profile row created through the USER_REGISTERED event
    assert client.get("/api/v1/auth/session", headers=headers).json()["data"]["user"]["FullName"] == "Ama Mensah"
    # unverified users may not use the rest of the API
    blocked = client.get("/api/v1/profiles/me", headers=headers)
    assert blocked.status_code == 403 and blocked.json()["code"] == "EMAIL_NOT_VERIFIED"


def test_register_validation_and_duplicates(client):
    assert _register(client, password="short", confirmPassword="short").json()["detail"] == \
        "Password must be at least 8 characters."
    assert _register(client, email="nope").json()["detail"] == "Please enter a valid email address."
    assert _register(client, firstName="").json()["detail"] == "First and last name are required."
    assert _register(client, confirmPassword="different1").json()["detail"] == "Passwords do not match."
    assert _register(client).status_code == 201
    dup = _register(client, email="ama@example.com")
    assert dup.status_code == 409 and dup.json()["code"] == "DUPLICATE_EMAIL"


def test_register_never_grants_admin_and_respects_settings(client, db):
    assert _register(client, role="Super Admin").json()["data"]["user"]["Role"] == "Professional"
    set_setting(db, "employerRegistration", "FALSE")
    closed = _register(client, email="boss@example.com", role="Employer")
    assert closed.json()["code"] == "EMPLOYER_REGISTRATION_DISABLED"
    set_setting(db, "registrationEnabled", "FALSE")
    assert _register(client, email="x@example.com").json()["code"] == "REGISTRATION_DISABLED"


def test_verify_email_flow(client, outbox):
    data = _register(client).json()["data"]
    headers = {"Authorization": f"Bearer {data['accessToken']}"}
    wrong = client.post("/api/v1/auth/verify-email", headers=headers, json={"code": "000000" if _code(outbox) != "000000" else "111111"})
    assert wrong.json()["code"] == "OTP_INVALID" and "4 attempts left" in wrong.json()["detail"]
    assert client.post("/api/v1/auth/verify-email", headers=headers, json={"code": "12"}).json()["detail"] == \
        "Enter the 6-digit code."
    ok = client.post("/api/v1/auth/verify-email", headers=headers, json={"code": _code(outbox)})
    assert ok.status_code == 200 and ok.json()["data"]["emailVerified"] is True
    assert outbox[-1]["subject"] == "Welcome to KoforLink"
    assert client.get("/api/v1/profiles/me", headers=headers).status_code == 200
    again = client.post("/api/v1/auth/verify-email", headers=headers, json={"code": "123456"})
    assert again.json()["message"] == "Email already verified."


def test_resend_cooldown_and_change_email(client, outbox, db):
    data = _register(client).json()["data"]
    headers = {"Authorization": f"Bearer {data['accessToken']}"}
    cooldown = client.post("/api/v1/auth/resend-code", headers=headers)
    assert cooldown.status_code == 429 and cooldown.json()["code"] == "RESEND_COOLDOWN"
    from app.modules.identity.models import VerificationCode
    record = db.query(VerificationCode).one()
    record.sent_at = utcnow() - timedelta(minutes=2)
    db.commit()
    assert client.post("/api/v1/auth/resend-code", headers=headers).json()["data"]["sent"] is True
    changed = client.post("/api/v1/auth/change-email", headers=headers, json={"email": "new@example.com"})
    assert changed.json()["data"]["email"] == "new@example.com" and outbox[-1]["to"] == "new@example.com"
    ok = client.post("/api/v1/auth/verify-email", headers=headers, json={"code": _code(outbox)})
    assert ok.json()["data"]["user"]["Email"] == "new@example.com"


def test_code_expiry_and_attempt_limit(client, outbox, db):
    data = _register(client).json()["data"]
    headers = {"Authorization": f"Bearer {data['accessToken']}"}
    code = _code(outbox)
    bad = "000000" if code != "000000" else "111111"
    for _ in range(5):
        client.post("/api/v1/auth/verify-email", headers=headers, json={"code": bad})
    assert client.post("/api/v1/auth/verify-email", headers=headers, json={"code": code}).json()["code"] == \
        "OTP_ATTEMPTS_EXCEEDED"
    from app.modules.identity.models import VerificationCode
    record = db.query(VerificationCode).one()
    record.attempts, record.expires_at = 0, utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.post("/api/v1/auth/verify-email", headers=headers, json={"code": code}).json()["code"] == "OTP_EXPIRED"


def test_login_lockout_and_status_checks(client, make_user, db):
    user = make_user(email="kwame@example.com")
    bad = {"email": "kwame@example.com", "password": "wrong-password"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=bad).json()["code"] == "INVALID_CREDENTIALS"
    locked = client.post("/api/v1/auth/login", json={"email": "kwame@example.com", "password": PASSWORD})
    assert locked.status_code == 423 and locked.json()["code"] == "ACCOUNT_LOCKED"
    db.refresh(user)
    assert user.locked_until > utcnow() + timedelta(minutes=14)  # the demo's lock was effectively 0 minutes
    user.locked_until, user.status = None, "Suspended"
    db.commit()
    assert client.post("/api/v1/auth/login", json={"email": "kwame@example.com", "password": PASSWORD}).json()["code"] == \
        "ACCOUNT_SUSPENDED"
    assert client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "x" * 8}).json()["code"] == \
        "INVALID_CREDENTIALS"


def test_login_refresh_logout(client, make_user):
    make_user(email="efua@example.com")
    login = client.post("/api/v1/auth/login", json={"email": "EFUA@example.com", "password": PASSWORD, "remember": True})
    assert login.status_code == 200 and login.json()["message"] == "Welcome back."
    tokens = login.json()["data"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert refreshed.status_code == 200
    new = refreshed.json()["data"]
    assert client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).status_code == 401  # rotated
    client.post("/api/v1/auth/logout", json={"refreshToken": new["refreshToken"]})
    assert client.post("/api/v1/auth/refresh", json={"refreshToken": new["refreshToken"]}).status_code == 401


def test_change_password_revokes_existing_tokens(client, make_user):
    user = make_user()
    old_headers = user.headers
    response = client.post("/api/v1/auth/change-password", headers=user.headers,
                           json={"currentPassword": PASSWORD, "newPassword": "brand-new-pass"})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/session", headers=old_headers).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": "brand-new-pass"}).status_code == 200
    wrong = client.post("/api/v1/auth/change-password", headers=user.headers,
                        json={"currentPassword": "nope-nope", "newPassword": "another-pass"})
    assert wrong.status_code == 401


def test_password_reset_by_code(client, make_user, outbox):
    user = make_user(email="yaw@example.com")
    generic = client.post("/api/v1/auth/password-reset", json={"email": "missing@example.com"})
    assert generic.status_code == 200 and not outbox
    client.post("/api/v1/auth/password-reset", json={"email": "yaw@example.com"})
    code = _code(outbox)
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 200
    confirm = client.post("/api/v1/auth/password-reset/confirm",
                          json={"email": "yaw@example.com", "code": code, "newPassword": "reset-pass-1"})
    assert confirm.status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": "reset-pass-1"}).status_code == 200
    reuse = client.post("/api/v1/auth/password-reset/confirm",
                        json={"email": "yaw@example.com", "code": code, "newPassword": "reset-pass-2"})
    assert reuse.json()["code"] == "NO_OTP"


def test_invalid_and_missing_tokens(client):
    assert client.get("/api/v1/auth/session").json()["code"] == "AUTH_REQUIRED"
    bad = client.get("/api/v1/auth/session", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401 and bad.json()["code"] == "AUTH_REQUIRED"
