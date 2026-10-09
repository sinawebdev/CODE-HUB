"""Request and response shapes for profiles (Pydantic models)."""
from pydantic import BaseModel, field_validator, model_validator

from app.core.schemas import ApiModel, Str, UserOut
from app.core.utils import safe_url


class ProfileUpdateIn(ApiModel):
    """Every field is optional: only the fields sent are changed."""

    first_name: Str(100) | None = None
    last_name: Str(100) | None = None
    phone: Str(40) | None = None
    professional_title: Str(160) | None = None
    email: Str(255) | None = None
    headline: Str(220) | None = None
    about: Str(4000) | None = None
    location: Str(150) | None = None
    country: Str(80) | None = None
    region: Str(80) | None = None
    city: Str(100) | None = None
    website: Str(500) | None = None
    languages: Str(500) | None = None
    achievements: Str(4000) | None = None
    interests: Str(1000) | None = None
    services: Str(1000) | None = None
    contact_email: Str(255) | None = None
    contact_phone: Str(40) | None = None
    profile_visibility: Str(20) | None = None
    contact_visibility: Str(20) | None = None
    location_visibility: Str(20) | None = None
    profile_photo: Str(32) | None = None
    cover_photo: Str(32) | None = None


class PhotoIn(ApiModel):
    kind: Str(10) = "profile"  # profile | cover
    file_id: Str(32)


class SkillIn(ApiModel):
    name: Str(80)
    level: Str(30) = ""

    @field_validator("name")
    @classmethod
    def required(cls, value: str) -> str:
        if not value:
            raise ValueError("Skill name is required.")
        return value


class ExperienceIn(ApiModel):
    title: Str(150) = ""
    company: Str(150) = ""
    location: Str(150) = ""
    start_date: Str(20) = ""
    end_date: Str(20) = ""
    current: bool = False
    description: Str(2000) = ""

    @model_validator(mode="after")
    def required(self) -> "ExperienceIn":
        if not self.title or not self.company:
            raise ValueError("Title and company are required.")
        return self


class EducationIn(ApiModel):
    school: Str(200) = ""
    degree: Str(200) = ""
    field: Str(200) = ""
    start_year: Str(10) = ""
    end_year: Str(10) = ""
    description: Str(2000) = ""

    @model_validator(mode="after")
    def required(self) -> "EducationIn":
        if not self.school:
            raise ValueError("School is required.")
        return self


class CertificationIn(ApiModel):
    name: Str(200) = ""
    issuer: Str(200) = ""
    issue_date: Str(20) = ""
    credential_id: Str(120) = ""
    credential_url: Str(500) = ""

    @model_validator(mode="after")
    def required(self) -> "CertificationIn":
        if not self.name:
            raise ValueError("Certification name is required.")
        return self

    @field_validator("credential_url")
    @classmethod
    def http_only(cls, value: str) -> str:
        return safe_url(value)


class ProjectIn(ApiModel):
    title: Str(200) = ""
    description: Str(2000) = ""
    url: Str(500) = ""
    start_date: Str(20) = ""
    end_date: Str(20) = ""

    @model_validator(mode="after")
    def required(self) -> "ProjectIn":
        if not self.title:
            raise ValueError("Project title is required.")
        return self

    @field_validator("url")
    @classmethod
    def http_only(cls, value: str) -> str:
        return safe_url(value)


class RestrictedUserOut(BaseModel):
    UserID: str
    FirstName: str
    LastName: str
    FullName: str
    Verified: bool


class ProfileFieldsOut(BaseModel):
    Headline: str
    About: str
    Location: str
    Country: str
    Region: str
    City: str
    ProfilePhoto: str | None
    ProfilePhotoUrl: str
    CoverPhoto: str | None
    CoverPhotoUrl: str
    Website: str
    Languages: str
    Achievements: str
    Interests: str
    Services: str
    ContactEmail: str
    ContactPhone: str
    ContactVisibility: str
    Visibility: str
    CompletionPct: int


class SkillOut(ApiModel):
    id: str
    name: str
    level: str
    endorsements: int


class ExperienceOut(ApiModel):
    id: str
    title: str
    company: str
    location: str
    start: str
    end: str
    current: bool
    description: str


class EducationOut(ApiModel):
    id: str
    school: str
    degree: str
    field: str
    start_year: str
    end_year: str
    description: str


class CertificationOut(ApiModel):
    id: str
    name: str
    issuer: str
    issue_date: str
    credential_id: str
    url: str


class ProjectOut(ApiModel):
    id: str
    title: str
    description: str
    url: str
    start: str
    end: str


class ProfileStatsOut(ApiModel):
    connections: int
    followers: int
    following: int
    posts: int


class RelationshipOut(ApiModel):
    connected: bool
    connection_id: str
    pending_outgoing: bool
    pending_incoming: bool
    following: bool
    blocked: bool
    mutual: int


class ProfilePageOut(ApiModel):
    restricted: bool
    user: UserOut | RestrictedUserOut
    message: str | None = None
    profile: ProfileFieldsOut | None = None
    skills: list[SkillOut] = []
    experience: list[ExperienceOut] = []
    education: list[EducationOut] = []
    certifications: list[CertificationOut] = []
    projects: list[ProjectOut] = []
    stats: ProfileStatsOut | None = None
    relationship: RelationshipOut | None = None


class PhotoOut(ApiModel):
    url: str
