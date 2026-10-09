"""Conversation and message shapes."""
from datetime import datetime
from pydantic import Field, model_validator
from app.core.schemas import ApiModel, Str


class StartIn(ApiModel):
    user_id: Str(32)
    message: Str(4000) = ""


class GroupIn(ApiModel):
    member_ids: list[Str(32)] = Field(default_factory=list, max_length=100)
    title: Str(150) = ""

    @model_validator(mode="after")
    def members_required(self):
        if not self.member_ids:
            raise ValueError("Select at least one member.")
        return self


class AttachmentIn(ApiModel):
    file_id: Str(32) = ""
    type: Str(20) = ""
    reply_to: Str(32) = ""


class MessageIn(ApiModel):
    body: Str(4000) = ""
    attachment: AttachmentIn | None = None

    @model_validator(mode="after")
    def content_required(self):
        if not self.body and not (self.attachment and self.attachment.file_id):
            raise ValueError("Message cannot be empty.")
        return self


class ReactionIn(ApiModel):
    type: Str(20) = "like"


class SettingsIn(ApiModel):
    pinned: bool | None = None
    muted: bool | None = None

    @model_validator(mode="after")
    def flag_required(self):
        if self.pinned is None and self.muted is None:
            raise ValueError("Unknown flag.")
        return self


class StartedOut(ApiModel):
    conversation_id: str


class LastMessageOut(ApiModel):
    body: str
    sender_id: str
    created_at: datetime
    time_ago: str


class ConversationOut(ApiModel):
    id: str
    type: str
    title: str
    avatar: str
    member_ids: list[str]
    member_count: int
    last_message: LastMessageOut | None
    last_message_at: datetime
    unread: int
    pinned: bool
    muted: bool


class ReactionOut(ApiModel):
    user_id: str
    type: str


class SentOut(ApiModel):
    id: str
    body: str
    mine: bool
    sender_id: str
    sender_name: str
    sender_photo: str
    attachment_url: str
    attachment_file_id: str
    attachment_type: str
    created_at: datetime
    time_ago: str
    reactions: list[ReactionOut]


class MessageOut(SentOut):
    deleted: bool
    reply_to: str
    status: str


class MessagesOut(ApiModel):
    messages: list[MessageOut]
    conversation: ConversationOut


class RemovedOut(ApiModel):
    removed: bool


class SearchOut(ApiModel):
    id: str
    body: str
    sender_id: str
    created_at: datetime
    time_ago: str
