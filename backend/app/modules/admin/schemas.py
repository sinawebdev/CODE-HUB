"""Request and response shapes for admin (Pydantic models)."""
from datetime import datetime

from app.core.schemas import ApiModel, Str, UserOut


class ReportIn(ApiModel):
    target_type: Str(20) = ""
    target_id: Str(32) = ""
    reason: Str(120) = ""
    details: Str(1000) = ""


class ReportReviewIn(ApiModel):
    status: Str(20)
    note: Str(500) = ""


class VerificationRequestIn(ApiModel):
    type: Str(20) = "user"  # user | company
    company_id: Str(32) | None = None
    note: Str(1000) = ""


class VerificationReviewIn(ApiModel):
    decision: Str(20)  # approve | reject | suspend
    reason: Str(500) = ""


class RoleIn(ApiModel):
    role: Str(30)


class StatusIn(ApiModel):
    status: Str(20)


class SettingsIn(ApiModel):
    """Booleans may be sent as true/false or 'TRUE'/'FALSE'; they are stored as 'TRUE'/'FALSE'."""

    platform_name: Str(500) | None = None
    logo_file_id: Str(32) | None = None
    primary_color: Str(500) | None = None
    secondary_color: Str(500) | None = None
    registration_enabled: bool | Str(5) | None = None
    employer_registration: bool | Str(5) | None = None
    email_notifications: bool | Str(5) | None = None
    maintenance_mode: bool | Str(5) | None = None
    default_city: Str(100) | None = None
    default_region: Str(100) | None = None


class TrendPointOut(ApiModel):
    label: str
    value: int


class AdminStatsOut(ApiModel):
    total_users: int
    active_users: int
    new_users: int
    companies: int
    jobs: int
    total_jobs: int
    applications: int
    posts: int
    reports: int
    events: int
    messages: int
    locations: int
    pending_verifications: int
    unverified_emails: int
    signup_trend: list[TrendPointOut]
    post_trend: list[TrendPointOut]
    role_breakdown: list[TrendPointOut]


class VerificationOut(ApiModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    user_photo: str
    user_role: str
    company_id: str
    company_name: str
    type: str
    document_file_id: str
    document_url: str
    notes: str
    status: str
    rejection_reason: str
    reviewed_by: str
    reviewed_at: datetime | None
    created_at: datetime
    time_ago: str


class AdminUserOut(UserOut):
    LastLogin: datetime | None = None
    FailedAttempts: int = 0
    LockedUntil: datetime | None = None
