"""HTTP endpoints for search. Keep these thin: validate input, call service, return schema."""
from fastapi import APIRouter

from app.core.database import DB
from app.core.permissions import OptionalUser
from app.core.schemas import Envelope, ok
from app.modules.search import service
from app.modules.search.schemas import SearchOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=Envelope[SearchOut])
def search(db: DB, viewer: OptionalUser, q: str = "", type: str = "all"):  # noqa: A002 - matches the demo's parameter
    return ok(service.search(db, viewer, q, type))
