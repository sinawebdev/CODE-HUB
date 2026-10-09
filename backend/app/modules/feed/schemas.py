"""Feed request and response contracts, retaining the demo's JSON names."""
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiModel, Str


class AuthorOut(ApiModel):
    user_id: str
    name: str
    headline: str = ""
    photo: str = ""
    verified: bool = False


class CompanyOut(ApiModel):
    id: str
    name: str
    logo: str = ""
    verified: bool = False


class MediaIn(ApiModel):
    file_id: Str(32)
    type: Literal["image", "video"] = "image"
    caption: Str(300) = ""


class MediaOut(MediaIn):
    id: str
    url: str


class PostIn(ApiModel):
    content: Str(5000) = ""
    media: list[MediaIn] = Field(default_factory=list, max_length=10)
    company_id: Str(32) | None = None
    visibility: Str(20) = "Public"
    repost_of: Str(32) | None = None

    @field_validator("content", mode="before")
    @classmethod
    def check_length(cls, value):
        if isinstance(value, str) and len(value.strip()) > 5000:
            raise ValueError("Post is too long.")
        return value

    @model_validator(mode="after")
    def require_content(self):
        if not self.content and not self.media:
            raise ValueError("Write something or attach media.")
        return self


class PostUpdateIn(ApiModel):
    content: Str(5000) = ""


class PostOut(ApiModel):
    id: str
    content: str
    created_at: datetime
    time_ago: str
    like_count: int
    comment_count: int
    share_count: int
    view_count: int
    liked: bool
    my_reaction: str
    saved: bool
    media_type: str
    media_url: str
    media: list[MediaOut]
    is_mine: bool
    author: AuthorOut
    company: CompanyOut | None = None
    repost_of: "PostOut | None" = None


class FeedOut(ApiModel):
    posts: list[PostOut]
    has_more: bool


class SkillOut(ApiModel):
    name: str
    count: int


class TrendingOut(ApiModel):
    posts: list[PostOut]
    skills: list[SkillOut]


class ReactionIn(ApiModel):
    type: Str(20) = "like"


class ReactionOut(ApiModel):
    liked: bool
    count: int
    type: str


class CommentIn(ApiModel):
    content: Str(2000) = ""
    parent_id: Str(32) | None = None

    @model_validator(mode="after")
    def require_content(self):
        if not self.content:
            raise ValueError("Comment cannot be empty.")
        return self


class CommentOut(ApiModel):
    id: str
    post_id: str
    parent_id: str
    content: str
    created_at: datetime
    time_ago: str
    is_mine: bool
    author: AuthorOut


class SavedOut(ApiModel):
    saved: bool


class ShareOut(ApiModel):
    url: str
