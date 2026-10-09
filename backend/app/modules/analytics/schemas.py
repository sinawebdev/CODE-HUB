"""Analytics response schemas."""
from app.core.schemas import ApiModel


class CountOut(ApiModel):
    label: str
    value: int


class PostEngagementOut(ApiModel):
    title: str
    likes: int
    comments: int


class CompanyAnalyticsOut(ApiModel):
    job_views: int
    jobs: int
    applications: int
    followers: int
    posts: int
    engagement: int
    post_engagement: list[PostEngagementOut]
    application_trend: list[CountOut]
    pipeline: list[CountOut]


class JobAnalyticsOut(ApiModel):
    views: int
    applications: int
    saves: int
