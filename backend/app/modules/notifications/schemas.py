"""Notification payloads."""
from datetime import datetime
from app.core.schemas import ApiModel


class NotificationOut(ApiModel):
    id: str
    type: str
    title: str
    body: str
    link: str
    read: bool
    created_at: datetime
    time_ago: str
    actor_photo: str


class NotificationsOut(ApiModel):
    notifications: list[NotificationOut]
    unread: int
