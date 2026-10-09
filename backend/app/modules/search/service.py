"""Business rules for search. Other modules may import from here, never from models.py."""
from sqlalchemy.orm import Session

from app.core.roles import ACTIVE
from app.core.utils import clean
from app.modules.companies import service as companies_service
from app.modules.feed import service as feed_service
from app.modules.identity import service_admin as users_admin
from app.modules.network import service as network_service
from app.modules.opportunities import service as opportunities_service
from app.modules.profiles import service as profiles_service

TYPES = ("all", "people", "companies", "jobs", "posts", "events", "skills")
LIMIT = 12


def _empty() -> dict:
    return {"people": [], "companies": [], "jobs": [], "posts": [], "events": [], "skills": []}


def search(db: Session, viewer, query: str, kind: str = "all") -> dict:
    """The demo's apiSearch: up to 12 results per type, hiding people the viewer blocked or was blocked by."""
    q = clean(query, 100)
    out = _empty()
    if len(q) < 2:
        return out
    kind = kind if kind in TYPES else "all"
    viewer_id = viewer.id if viewer is not None else None
    hidden = network_service.blocked_user_ids(db, viewer_id) if viewer_id else set()
    wants = lambda name: kind in ("all", name)  # noqa: E731
    if wants("people"):
        ids = [u.id for u in users_admin.search_users(db, q, limit=50, exclude_ids=hidden)]
        ids += [uid for uid in profiles_service.user_ids_with_headline(db, q) if uid not in ids and uid not in hidden]
        cards = profiles_service.user_cards(db, ids)
        out["people"] = [
            {key: card[key] for key in ("userId", "name", "headline", "photo", "city", "verified")}
            for card in (cards.get(uid) for uid in ids) if card and card["status"] == ACTIVE
        ][:LIMIT]
    if wants("companies"):
        out["companies"] = companies_service.search_companies(db, q, viewer_id, LIMIT)
        counts = opportunities_service.open_job_counts(db, [c["id"] for c in out["companies"]])
        for company in out["companies"]:
            company["jobCount"] = counts.get(company["id"], 0)
    if wants("jobs"):
        out["jobs"] = opportunities_service.search_jobs(db, q, viewer_id, LIMIT)
    if wants("posts"):
        posts = feed_service.search_posts(db, q, viewer_id, LIMIT * 2)
        out["posts"] = [p for p in posts if p["author"]["userId"] not in hidden][:LIMIT]
    if wants("events"):
        out["events"] = opportunities_service.search_events(db, q, LIMIT)
    if wants("skills"):
        out["skills"] = profiles_service.search_skills(db, q, LIMIT)
    return out
