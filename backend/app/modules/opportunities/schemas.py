"""Job, application, and event schemas."""
from datetime import date, datetime
from pydantic import field_validator, model_validator
from app.core.schemas import ApiModel, Str
from app.core.utils import to_float


class JobIn(ApiModel):
    company_id: Str(32) = ""
    title: Str(200) = ""
    description: Str(6000) = ""
    responsibilities: Str(6000) = ""
    requirements: Str(6000) = ""
    skills: Str(1000) = ""
    salary: Str(200) = ""
    salary_min: float | None = None
    salary_max: float | None = None
    currency: Str(10) = "GHS"
    employment_type: Str(30) = "Full-time"
    experience_level: Str(30) = "Mid"
    deadline: date | None = None
    work_arrangement: Str(30) = "On-site"
    location_id: Str(32) = ""
    city: Str(100) = "Koforidua"
    region: Str(80) = "Eastern Region"
    status: Str(20) = "Open"

    @field_validator("salary_min", "salary_max", mode="before")
    @classmethod
    def number(cls, value):
        return to_float(value)

    @field_validator("deadline", mode="before")
    @classmethod
    def blank_date(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def required_title(self):
        if not self.title:
            raise ValueError("Job title is required.")
        return self


class JobUpdateIn(ApiModel):
    title: Str(200) | None = None
    description: Str(6000) | None = None
    responsibilities: Str(6000) | None = None
    requirements: Str(6000) | None = None
    skills: Str(1000) | None = None
    salary: Str(200) | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    employment_type: Str(30) | None = None
    experience_level: Str(30) | None = None
    deadline: date | None = None
    work_arrangement: Str(30) | None = None
    status: Str(20) | None = None

    @field_validator("salary_min", "salary_max", mode="before")
    @classmethod
    def number(cls, value):
        return to_float(value)

    @field_validator("deadline", mode="before")
    @classmethod
    def blank_date(cls, value):
        return None if value == "" else value

    @field_validator("title")
    @classmethod
    def required_title(cls, value):
        if not value:
            raise ValueError("Job title is required.")
        return value


class ApplicationIn(ApiModel):
    cover_letter: Str(4000) = ""
    cv_file_id: Str(32) = ""


class ApplicationStatusIn(ApiModel):
    status: Str(20)


class JobAlertIn(ApiModel):
    keywords: Str(200) = ""
    location: Str(120) = ""
    employment_type: Str(30) = ""
    work_arrangement: Str(30) = ""
    min_salary: float | None = None
    frequency: Str(20) = "Daily"

    @field_validator("min_salary", mode="before")
    @classmethod
    def number(cls, value):
        return to_float(value)


class EventIn(ApiModel):
    title: Str(250) = ""
    description: Str(5000) = ""
    company_id: Str(32) = ""
    event_date: date | None = None
    start_time: Str(20) = ""
    end_time: Str(20) = ""
    location_name: Str(250) = ""
    address: Str(400) = ""
    city: Str(100) = "Koforidua"
    region: Str(80) = "Eastern Region"
    latitude: float | None = None
    longitude: float | None = None
    cover_image: Str(32) = ""
    registration_required: bool = False
    max_attendees: int = 0

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coordinates(cls, value):
        return to_float(value)

    @field_validator("event_date", mode="before")
    @classmethod
    def valid_date(cls, value):
        if value is None or value == "":
            raise ValueError("Event date is required.")
        try:
            return value if isinstance(value, date) else date.fromisoformat(value)
        except (ValueError, TypeError):
            raise ValueError("Invalid event date.")

    @model_validator(mode="after")
    def required_fields(self):
        if not self.title:
            raise ValueError("Event title is required.")
        if self.event_date is None:
            raise ValueError("Event date is required.")
        return self


class EventUpdateIn(ApiModel):
    title: Str(250) | None = None
    description: Str(5000) | None = None
    event_date: date | None = None
    start_time: Str(20) | None = None
    end_time: Str(20) | None = None
    location_name: Str(250) | None = None
    address: Str(400) | None = None
    city: Str(100) | None = None
    region: Str(80) | None = None
    latitude: float | None = None
    longitude: float | None = None
    max_attendees: int | None = None
    status: Str(20) | None = None

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coordinates(cls, value):
        return to_float(value)

    @field_validator("event_date", mode="before")
    @classmethod
    def valid_date(cls, value):
        return EventIn.valid_date(value)

    @field_validator("title")
    @classmethod
    def required_title(cls, value):
        if not value:
            raise ValueError("Event title is required.")
        return value


class AttendanceIn(ApiModel):
    status: Str(20)


class CompanyBadgeOut(ApiModel):
    id: str
    name: str
    logo: str


class JobCompanyOut(CompanyBadgeOut):
    verified: bool
    industry: str


class JobLocationOut(ApiModel):
    id: str
    name: str
    city: str
    address: str
    region: str


class JobOut(ApiModel):
    id: str
    title: str
    description: str
    responsibilities: str
    requirements: str
    skills: list[str]
    salary: str
    salary_min: float | None
    salary_max: float | None
    currency: str
    employment_type: str
    experience_level: str
    deadline: date | None
    deadline_passed: bool
    work_arrangement: str
    city: str
    region: str
    country: str
    latitude: float | None
    longitude: float | None
    status: str
    views: int
    created_at: datetime
    time_ago: str
    saved: bool
    applied: bool
    application_status: str
    company: JobCompanyOut | None
    location: JobLocationOut | None
    applicant_count: int


class NearbyJobOut(JobOut):
    distance: float


class SavedOut(ApiModel):
    saved: bool


class ApplicationIdOut(ApiModel):
    application_id: str


class ApplicationJobOut(ApiModel):
    id: str
    title: str
    city: str


class MyApplicationOut(ApiModel):
    id: str
    status: str
    stage: str
    created_at: datetime
    time_ago: str
    job: ApplicationJobOut
    company: CompanyBadgeOut | None


class ApplicantOut(ApiModel):
    user_id: str
    name: str
    headline: str
    photo: str
    city: str
    email: str


class ApplicationOut(ApiModel):
    id: str
    status: str
    stage: str
    cover_letter: str
    cv_url: str
    cv_file_id: str
    created_at: datetime
    time_ago: str
    applicant: ApplicantOut


class OrganizerOut(ApiModel):
    user_id: str
    name: str


class EventOut(ApiModel):
    id: str
    title: str
    description: str
    event_date: date
    start_time: str
    end_time: str
    location_name: str
    address: str
    city: str
    region: str
    latitude: float | None
    longitude: float | None
    cover_image: str
    registration_required: bool
    max_attendees: int
    attendee_count: int
    status: str
    created_at: datetime
    is_past: bool
    organizer: OrganizerOut | None
    company: CompanyBadgeOut | None
    maps_link: str


class EventPageOut(EventOut):
    can_manage: bool
    my_status: str


class AttendanceOut(ApiModel):
    status: str
