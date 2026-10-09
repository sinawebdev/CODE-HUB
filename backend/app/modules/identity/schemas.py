"""Request and response shapes for identity (Pydantic models)."""
import re
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiModel, Str, UserOut

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def _email(value: str) -> str:
    value = (value or "").strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("Please enter a valid email address.")
    return value


class RegisterIn(ApiModel):
    first_name: Str(100) = ""
    last_name: Str(100) = ""
    email: Str(255)
    phone: Str(40) = ""
    password: str = Field(max_length=200)
    confirm_password: str = Field(max_length=200)
    city: Str(100) = ""
    professional_title: Str(160) = ""
    role: Str(30) = "Professional"

    @model_validator(mode="after")
    def names_required(self) -> "RegisterIn":
        if not self.first_name or not self.last_name:
            raise ValueError("First and last name are required.")
        return self

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _email(value)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return value


class LoginIn(ApiModel):
    email: Str(255) = ""
    password: str = Field("", max_length=200)
    remember: bool = False


class RefreshIn(ApiModel):
    refresh_token: str = Field(max_length=200)


class LogoutIn(ApiModel):
    refresh_token: str | None = Field(None, max_length=200)


class VerifyEmailIn(ApiModel):
    code: Str(20)


class ChangeEmailIn(ApiModel):
    email: Str(255)


class ChangePasswordIn(ApiModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


class PasswordResetIn(ApiModel):
    email: Str(255)


class PasswordResetConfirmIn(ApiModel):
    email: Str(255)
    code: Str(20)
    new_password: str = Field(max_length=200)


class AuthOut(ApiModel):
    access_token: str
    refresh_token: str
    expires_at: datetime
    user: UserOut
    email_verified: bool
    email: str | None = None


class SessionOut(ApiModel):
    user: UserOut
    email_verified: bool


class VerifyEmailOut(ApiModel):
    email_verified: bool
    user: UserOut


class ResendOut(ApiModel):
    sent: bool
    email_verified: bool


class ChangeEmailOut(ApiModel):
    email: str
