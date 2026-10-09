"""HTTP endpoints for identity. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter, Request

from app.core.database import DB
from app.core.permissions import CurrentUser
from app.core.schemas import Envelope, ok
from app.modules.identity import schemas
from app.modules.identity import service

router = APIRouter(prefix="/auth", tags=["identity"])


def _agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


@router.post("/register", status_code=201, response_model=Envelope[schemas.AuthOut])
def register(body: schemas.RegisterIn, request: Request, db: DB):
    return ok(service.register(db, body, _agent(request)), "Account created. Please verify your email.")


@router.post("/login", response_model=Envelope[schemas.AuthOut])
def login(body: schemas.LoginIn, request: Request, db: DB):
    data, message = service.login(db, body.email, body.password, body.remember, _agent(request))
    return ok(data, message)


@router.post("/refresh", response_model=Envelope[schemas.AuthOut])
def refresh(body: schemas.RefreshIn, request: Request, db: DB):
    return ok(service.refresh_session(db, body.refresh_token, _agent(request)))


@router.post("/logout", response_model=Envelope[None])
def logout(body: schemas.LogoutIn, db: DB):
    service.logout(db, body.refresh_token)
    return ok(None, "Signed out.")


@router.get("/session", response_model=Envelope[schemas.SessionOut])
def session(user: CurrentUser):
    return ok({"user": service.safe_user(user, True), "emailVerified": user.email_verified})


@router.post("/verify-email", response_model=Envelope[schemas.VerifyEmailOut])
def verify_email(body: schemas.VerifyEmailIn, user: CurrentUser, db: DB):
    data, message = service.verify_email(db, user, body.code)
    return ok(data, message)


@router.post("/resend-code", response_model=Envelope[schemas.ResendOut])
def resend_code(user: CurrentUser, db: DB):
    already = user.email_verified
    message = service.resend_verification(db, user)
    return ok({"sent": not already, "emailVerified": already}, message)


@router.post("/change-email", response_model=Envelope[schemas.ChangeEmailOut])
def change_email(body: schemas.ChangeEmailIn, user: CurrentUser, db: DB):
    email = service.change_unverified_email(db, user, body.email)
    return ok({"email": email}, f"A new code has been sent to {email}.")


@router.post("/change-password", response_model=Envelope[None])
def change_password(body: schemas.ChangePasswordIn, user: CurrentUser, db: DB):
    service.change_password(db, user, body.current_password, body.new_password)
    return ok(None, "Password updated. Please sign in again.")


@router.post("/password-reset", response_model=Envelope[None])
def request_password_reset(body: schemas.PasswordResetIn, db: DB):
    service.request_password_reset(db, body.email)
    return ok(None, service.RESET_SENT)


@router.post("/password-reset/confirm", response_model=Envelope[None])
def confirm_password_reset(body: schemas.PasswordResetConfirmIn, db: DB):
    service.confirm_password_reset(db, body.email, body.code, body.new_password)
    return ok(None, "Password updated. You can now sign in.")
