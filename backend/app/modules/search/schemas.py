"""Request and response shapes for search (Pydantic models)."""
from typing import Any

from app.core.schemas import ApiModel


class PersonResultOut(ApiModel):
    user_id: str
    name: str
    headline: str
    photo: str
    city: str
    verified: bool


class SkillResultOut(ApiModel):
    id: str
    name: str
    category: str


class SearchOut(ApiModel):
    """Companies, jobs, posts and events use the same shapes as their own modules' endpoints."""

    people: list[PersonResultOut]
    companies: list[dict[str, Any]]
    jobs: list[dict[str, Any]]
    posts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    skills: list[SkillResultOut]
