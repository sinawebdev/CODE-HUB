"""HTTP endpoints for platform. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter

from app.core.config import settings
from app.core.database import DB
from app.core.permissions import OptionalUser
from app.core.roles import is_admin, is_staff
from app.core.schemas import Envelope, ok
from app.modules.identity import service as identity_service
from app.modules.messaging import service as messaging_service
from app.modules.network import service as network_service
from app.modules.notifications import service as notifications_service
from app.modules.platform import service
from app.modules.platform.schemas import BootstrapOut
from app.modules.profiles import service as profiles_service

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/bootstrap", response_model=Envelope[BootstrapOut])
def bootstrap(db: DB, user: OptionalUser):
    """Public settings for everyone; plus the user, badge counts and roles when signed in."""
    data = {
        "authenticated": user is not None,
        "settings": service.get_settings(db, service.PUBLIC_KEYS),
        "app": {"name": settings.app_name, "version": settings.app_version},
    }
    if user is not None:
        data.update(
            user=identity_service.safe_user(user, include_contact=True),
            profilePhoto=profiles_service.profile_photo_url(db, user.id),
            counts={
                "notifications": notifications_service.unread_count(db, user.id),
                "messages": messaging_service.unread_message_count(db, user.id),
                "connectionRequests": network_service.pending_request_count(db, user.id),
            },
            isStaff=is_staff(user.role), isAdmin=is_admin(user.role), emailVerified=user.email_verified,
        )
    return ok(data)
