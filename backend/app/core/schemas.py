"""Shared Pydantic building blocks: camelCase JSON in and out, and the response envelope."""
from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

T = TypeVar("T")


def Str(max_length: int):  # noqa: N802 - used like a type: `headline: Str(220) = ""`
    """A trimmed string capped at max_length characters."""
    return Annotated[str, StringConstraints(strip_whitespace=True, max_length=max_length)]


class ApiModel(BaseModel):
    """Request/response model: Python attributes are snake_case, JSON keys are camelCase."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Envelope(BaseModel, Generic[T]):
    """Every successful response: {"data": ..., "message": "..."}. Errors use {"detail", "code"}."""

    data: T | None = None
    message: str = "OK"


class UserOut(BaseModel):
    """A user exactly as the frontend expects it (sheet-style keys inherited from the demo)."""

    UserID: str
    FirstName: str
    LastName: str
    FullName: str
    Role: str
    Status: str
    City: str
    ProfessionalTitle: str
    Verified: bool
    EmailVerified: bool
    CreatedAt: datetime
    Email: str | None = None  # only for the user themself / staff
    Phone: str | None = None


def ok(data: Any = None, message: str = "OK") -> dict:
    return {"data": data, "message": message}
