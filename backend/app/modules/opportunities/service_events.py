"""Events, registration, and company event interfaces."""
from collections import Counter
from urllib.parse import quote
from sqlalchemy import func, or_, select
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.roles import is_staff
from app.core.utils import is_past
from app.modules.companies import service as companies_service
from app.modules.media import service as media_service
from app.modules.opportunities.models import Event, EventAttendee
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service

EVENT_STATUSES = ("Active", "Cancelled", "Completed")
ATTENDANCE_STATUSES = ("Attending", "Maybe", "Declined")


def can_manage(user, event):
    return bool(user and (event.organizer_id == user.id or is_staff(user.role)))


def require_event(db, event_id, user=None, manage=False, lock=False):
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update()) if lock else db.get(Event, event_id)
    if event is None:
        raise not_found("Event not found.")
    if manage and not can_manage(user, event):
        raise forbidden("Not allowed.")
    return event


def hydrate_events(db, event_list):
    event_list = list(event_list)
    ids = [e.id for e in event_list]
    if not ids:
        return []
    cards = profiles_service.user_cards(db, [e.organizer_id for e in event_list])
    companies = companies_service.company_summaries(db, [e.company_id for e in event_list])
    counts = dict(db.execute(select(EventAttendee.event_id, func.count()).where(
        EventAttendee.event_id.in_(ids), EventAttendee.status == "Attending").group_by(EventAttendee.event_id)).all())
    result = []
    for event in event_list:
        card = cards.get(event.organizer_id)
        company = companies.get(event.company_id)
        query = f"{event.latitude},{event.longitude}" if event.latitude is not None and event.longitude is not None else (
            ", ".join(v for v in (event.location_name, event.address, event.city, event.region) if v) or "Koforidua")
        data = {k: getattr(event, k) for k in ("id", "title", "description", "address", "city",
                                              "region", "latitude", "longitude", "status")}
        data.update(eventDate=event.event_date, startTime=event.start_time, endTime=event.end_time,
                    locationName=event.location_name, coverImage=media_service.media_url(event.cover_image),
                    registrationRequired=event.registration_required, maxAttendees=event.max_attendees,
                    attendeeCount=counts.get(event.id, 0), createdAt=event.created_at,
                    isPast=is_past(event.event_date),
                    organizer={"userId": card["userId"], "name": card["name"]} if card else None,
                    company={k: company[k] for k in ("id", "name", "logo")} if company else None,
                    mapsLink="https://www.google.com/maps/search/?api=1&query=" + quote(query, safe=""))
        result.append(data)
    return result


def create_event(db, user, data):
    data = dict(data)
    if is_past(data["event_date"]):
        raise bad_request("Event date cannot be in the past.")
    company_id = data.pop("company_id")
    company = companies_service.get_company(db, company_id)
    # The demo simply leaves company affiliation empty unless the organizer manages it.
    company_id = company.id if companies_service.can_manage(db, user, company) else None
    if data["cover_image"]:
        file = media_service.owned_file(db, user.id, data["cover_image"], ("Event Images",))
        if not file.mime_type.startswith("image/"):
            raise bad_request("Invalid file. Please upload it again.", "INVALID_FILE")
        data["cover_image"] = file.id
    data["max_attendees"] = max(data["max_attendees"], 0)
    for field, setting in (("city", "defaultCity"), ("region", "defaultRegion")):
        data[field] = data[field] or platform_service.get_setting(db, setting)
    event = Event(**data, organizer_id=user.id, company_id=company_id)
    db.add(event)
    db.flush()
    platform_service.audit(db, user.id, "CREATE_EVENT", "Event", event.id, "")
    db.commit()
    return hydrate_events(db, [event])[0]


def list_events(db, query="", city="", upcoming=False, limit=None):
    stmt = select(Event).where(Event.status != "Cancelled").order_by(Event.event_date)
    if query:
        stmt = stmt.where(or_(*(col.icontains(query, autoescape=True)
                               for col in (Event.title, Event.description, Event.city))))
    if city:
        stmt = stmt.where(func.lower(Event.city) == city.lower())
    if upcoming:
        from app.core.utils import utcnow
        stmt = stmt.where(Event.event_date >= utcnow().date())
    if limit is not None:
        stmt = stmt.limit(limit)
    return hydrate_events(db, db.scalars(stmt))


def event_page(db, event_id, viewer):
    event = require_event(db, event_id)
    payload = hydrate_events(db, [event])[0]
    attendance = db.scalar(select(EventAttendee).where(
        EventAttendee.event_id == event_id, EventAttendee.user_id == viewer.id)) if viewer else None
    payload.update(canManage=can_manage(viewer, event), myStatus=attendance.status if attendance else "")
    return payload


def attendance(db, user, event_id, status):
    event = require_event(db, event_id, lock=True)
    if event.status == "Cancelled":
        raise conflict("This event has been cancelled.", "EVENT_CANCELLED")
    if event.status == "Completed":
        raise conflict("This event has ended.", "EVENT_ENDED")
    existing = db.scalar(select(EventAttendee).where(
        EventAttendee.event_id == event_id, EventAttendee.user_id == user.id))
    if status == "cancel":
        if existing:
            db.delete(existing)
        db.commit()
        return "none", "Registration cancelled."
    if status not in ATTENDANCE_STATUSES:
        raise bad_request("Invalid attendance status.")
    if event.registration_required and status == "Attending" and event.max_attendees > 0:
        stmt = select(func.count()).select_from(EventAttendee).where(
            EventAttendee.event_id == event_id, EventAttendee.status == "Attending")
        if existing:
            stmt = stmt.where(EventAttendee.id != existing.id)
        if db.scalar(stmt) >= event.max_attendees:
            raise conflict("This event is full.", "EVENT_FULL")
    if existing:
        existing.status = status
        message = "Response updated."
    else:
        db.add(EventAttendee(event_id=event_id, user_id=user.id, status=status))
        message = "You are registered."
    db.commit()
    return status, message


def my_events(db, user):
    return hydrate_events(db, db.scalars(select(Event).join(
        EventAttendee, EventAttendee.event_id == Event.id).where(EventAttendee.user_id == user.id)))


def update_event(db, user, event_id, data):
    event = require_event(db, event_id, user, True)
    if "status" in data and data["status"] not in EVENT_STATUSES:
        raise bad_request("Invalid event status.")
    if "event_date" in data and is_past(data["event_date"]):
        raise bad_request("Event date cannot be in the past.")
    for key, value in data.items():
        if key == "max_attendees":
            value = max(value or 0, 0)
        elif key not in ("latitude", "longitude", "event_date"):
            value = value or ""
        setattr(event, key, value)
    platform_service.audit(db, user.id, "UPDATE_EVENT", "Event", event.id, "")
    db.commit()
    return hydrate_events(db, [event])[0]


def delete_event(db, user, event_id):
    event = require_event(db, event_id, user, True)
    event.status = "Cancelled"
    platform_service.audit(db, user.id, "CANCEL_EVENT", "Event", event.id, "")
    db.commit()


def company_events(db, company_id):
    return hydrate_events(db, db.scalars(select(Event).where(
        Event.company_id == company_id, Event.status != "Cancelled")))


def search_events(db, query, limit=12):
    return list_events(db, query=query, limit=limit)
