"""Role checks (user, company_admin, moderator, admin) used as FastAPI dependencies.

Routers declare who may call them with the Annotated aliases at the bottom, e.g.
`def endpoint(user: VerifiedUser, db: DB)`. Company-admin checks live in the
companies service (`can_manage`) because they depend on company membership.
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import forbidden, unauthorized
from app.core.roles import ADMIN_ROLES, STAFF_ROLES
from app.core.security import decode_access_token
from app.modules.identity import service as identity_service
from app.modules.identity.models import User  # the one place outside identity that names the type
from app.modules.platform import service as platform_service

_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User | None:
    """Anonymous when no token is sent; 401 when a token is sent but expired, revoked or invalid."""
    if credentials is None:
        return None
    user = identity_service.user_for_token(db, decode_access_token(credentials.credentials))
    if user is None:
        raise unauthorized()
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    """Signed in (email may still be unverified: used by the verification endpoints)."""
    if user is None:
        raise unauthorized()
    return user


def get_verified_user(user: User = Depends(get_current_user)) -> User:
    """Signed in with a verified email: required by everything except auth itself."""
    if not user.email_verified:
        raise forbidden("Please verify your email to continue.", "EMAIL_NOT_VERIFIED")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_verified_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return dependency


def maintenance_guard(user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)) -> None:
    """Router-level dependency: only staff get through while maintenance mode is on."""
    platform_service.assert_not_in_maintenance(db, user.role if user else None)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(get_verified_user)]
StaffUser = Annotated[User, Depends(require_roles(*STAFF_ROLES))]
AdminUser = Annotated[User, Depends(require_roles(*ADMIN_ROLES))]
