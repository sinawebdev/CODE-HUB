"""Company and workplace API schemas."""
from datetime import datetime
from typing import Literal
from pydantic import Field, field_validator, model_validator
from app.core.schemas import ApiModel, Str
from app.core.utils import to_float
from app.modules.feed.schemas import PostOut
from app.modules.opportunities.schemas import EventOut, JobOut


class CompanyIn(ApiModel):
    name: Str(200) = ""
    industry: Str(120) = ""
    description: Str(4000) = ""
    website: Str(500) = ""
    email: Str(200) = ""
    phone: Str(60) = ""
    founded: Str(20) = ""
    size: Str(20) = ""
    your_title: Str(150) = "Owner"

    @model_validator(mode="after")
    def required_name(self):
        if not self.name:
            raise ValueError("Company name is required.")
        return self


class CompanyUpdateIn(ApiModel):
    name: Str(200) | None = None
    industry: Str(120) | None = None
    description: Str(4000) | None = None
    website: Str(500) | None = None
    email: Str(200) | None = None
    phone: Str(60) | None = None
    founded: Str(20) | None = None
    size: Str(20) | None = None

    @field_validator("name")
    @classmethod
    def required_name(cls, value):
        if not value:
            raise ValueError("Company name is required.")
        return value


class ImageIn(ApiModel):
    kind: Literal["logo", "cover"] = "logo"
    file_id: Str(32)


class PhotoIn(ApiModel):
    file_id: Str(32)
    category: Str(60) = "General"
    caption: Str(300) = ""


class OfferingIn(ApiModel):
    name: Str(150) = ""
    description: Str(800) = ""

    @model_validator(mode="after")
    def required_name(self):
        if not self.name:
            raise ValueError("Service name is required.")
        return self


class LocationIn(ApiModel):
    name: Str(200) = ""
    address: Str(400) = ""
    country: Str(80) = "Ghana"
    region: Str(80) = "Eastern Region"
    city: Str(100) = "Koforidua"
    area: Str(150) = ""
    ghana_post_gps: Str(40) = ""
    landmark: Str(200) = ""
    latitude: float | None = None
    longitude: float | None = None
    phone: Str(60) = ""
    email: Str(200) = ""
    opening_time: Str(20) = ""
    closing_time: Str(20) = ""
    is_hq: bool = Field(default=False, alias="isHQ")

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coordinates(cls, value):
        return to_float(value)

    @model_validator(mode="after")
    def required_name(self):
        if not self.name:
            raise ValueError("Workplace name is required.")
        return self


class LocationUpdateIn(ApiModel):
    name: Str(200) | None = None
    address: Str(400) | None = None
    country: Str(80) | None = None
    region: Str(80) | None = None
    city: Str(100) | None = None
    area: Str(150) | None = None
    ghana_post_gps: Str(40) | None = None
    landmark: Str(200) | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: Str(60) | None = None
    email: Str(200) | None = None
    opening_time: Str(20) | None = None
    closing_time: Str(20) | None = None
    is_hq: bool | None = Field(default=None, alias="isHQ")

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coordinates(cls, value):
        return to_float(value)

    @field_validator("name")
    @classmethod
    def required_name(cls, value):
        if not value:
            raise ValueError("Workplace name is required.")
        return value


class UrlOut(ApiModel):
    url: str


class LocationPhotoOut(ApiModel):
    id: str
    file_id: str
    url: str
    category: str
    caption: str


class LocationOut(ApiModel):
    id: str
    company_id: str
    name: str
    address: str
    country: str
    region: str
    city: str
    area: str
    ghana_post_gps: str
    landmark: str
    latitude: float | None
    longitude: float | None
    phone: str
    email: str
    opening_time: str
    closing_time: str
    is_hq: bool = Field(alias="isHQ")
    photos: list[LocationPhotoOut]
    photo_count: int
    maps_link: str
    directions_link: str


class HqOut(ApiModel):
    city: str
    region: str
    country: str
    address: str


class CompanyOut(ApiModel):
    id: str
    name: str
    slug: str
    industry: str
    description: str
    website: str
    email: str
    phone: str
    founded: str
    size: str
    logo: str
    logo_id: str
    cover: str
    cover_id: str
    verified: bool
    status: str
    owner_id: str
    created_at: datetime
    location_count: int
    hq: HqOut | None
    employee_count: int
    job_count: int
    is_member: bool
    is_owner: bool


class NearbyCompanyOut(CompanyOut):
    distance: float
    near_location: LocationOut


class MemberOut(ApiModel):
    user_id: str
    name: str
    title: str
    role: str
    photo: str
    verified: bool


class OfferingOut(ApiModel):
    id: str
    name: str
    description: str


class CompanyPageOut(CompanyOut):
    members: list[MemberOut]
    locations: list[LocationOut]
    services: list[OfferingOut]
    jobs: list[JobOut]
    posts: list[PostOut]
    events: list[EventOut]
    can_manage: bool
