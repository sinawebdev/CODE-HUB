"""Role and account-status names shared by every module."""

SUPER_ADMIN = "Super Admin"
ADMIN = "Admin"
MODERATOR = "Moderator"
EMPLOYER = "Employer"
PROFESSIONAL = "Professional"
STUDENT = "Student"
NORMAL_USER = "Normal User"

ALL_ROLES = (SUPER_ADMIN, ADMIN, MODERATOR, EMPLOYER, PROFESSIONAL, STUDENT, NORMAL_USER)
ADMIN_ROLES = (SUPER_ADMIN, ADMIN)
STAFF_ROLES = (SUPER_ADMIN, ADMIN, MODERATOR)

ACTIVE = "Active"
USER_STATUSES = (ACTIVE, "Suspended", "Disabled", "Pending")


def is_staff(role: str | None) -> bool:
    return role in STAFF_ROLES


def is_admin(role: str | None) -> bool:
    return role in ADMIN_ROLES
