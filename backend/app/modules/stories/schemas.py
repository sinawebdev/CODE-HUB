"""Story request and display contracts."""
from datetime import datetime
from typing import Literal

from pydantic import model_validator

from app.core.schemas import ApiModel, Str


class StoryIn(ApiModel):
    file_id: Str(32) = ""
    type: Literal["image", "video"] = "image"
    caption: Str(300) = ""

    @model_validator(mode="after")
    def require_file(self):
        if not self.file_id:
            raise ValueError("A photo or video is required.")
        return self


class StoryUserOut(ApiModel):
    user_id: str
    name: str
    photo: str
    verified: bool


class StoryOut(ApiModel):
    id: str
    user_id: str
    user: StoryUserOut
    file_id: str
    url: str
    type: str
    caption: str
    view_count: int
    viewed: bool
    expires_at: datetime
    created_at: datetime
    is_mine: bool


class StoryGroupOut(ApiModel):
    user_id: str
    user: StoryUserOut
    story_count: int
    has_unviewed: bool
    is_mine: bool
    stories: list[StoryOut]


class ViewOut(ApiModel):
    view_count: int
