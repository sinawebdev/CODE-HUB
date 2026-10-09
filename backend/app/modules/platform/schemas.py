"""Request and response shapes for platform (Pydantic models)."""
from app.core.schemas import ApiModel, UserOut


class AppInfoOut(ApiModel):
    name: str
    version: str


class CountsOut(ApiModel):
    notifications: int
    messages: int
    connection_requests: int


class BootstrapOut(ApiModel):
    """What the frontend needs on load. Settings values are strings; booleans are 'TRUE'/'FALSE'."""

    authenticated: bool
    settings: dict[str, str]
    app: AppInfoOut
    user: UserOut | None = None
    profile_photo: str = ""
    counts: CountsOut | None = None
    is_staff: bool = False
    is_admin: bool = False
    email_verified: bool = False
