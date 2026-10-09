"""Network requests and member cards."""
from datetime import datetime
from app.core.schemas import ApiModel, Str


class ConnectionIn(ApiModel):
    user_id: Str(32)
    message: Str(300) = ""


class RespondIn(ApiModel):
    action: Str(20) = ""


class PersonOut(ApiModel):
    user_id: str
    name: str
    headline: str
    photo: str


class ConnectionOut(PersonOut):
    connection_id: str
    verified: bool
    city: str


class OutgoingOut(PersonOut):
    connection_id: str
    created_at: datetime


class IncomingOut(OutgoingOut):
    message: str
    mutual: int


class RequestsOut(ApiModel):
    incoming: list[IncomingOut]
    outgoing: list[OutgoingOut]


class SuggestionOut(PersonOut):
    city: str
    verified: bool
    mutual: int
    score: int


class BlockedOut(ApiModel):
    user_id: str
    name: str
