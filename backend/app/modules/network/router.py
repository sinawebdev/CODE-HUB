"""Connection, follow and block endpoints."""
from fastapi import APIRouter, Query
from app.core.database import DB
from app.core.permissions import VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.network import schemas, service

router = APIRouter(prefix="/network", tags=["network"])


@router.post("/connections", response_model=Envelope[None])
def send_connection(body: schemas.ConnectionIn, user: VerifiedUser, db: DB):
    return ok(message=service.send_connection(db, user, body.user_id, body.message))


@router.post("/connections/{connection_id}/respond", response_model=Envelope[None])
def respond(connection_id: str, body: schemas.RespondIn, user: VerifiedUser, db: DB):
    return ok(message=service.respond_connection(db, user, connection_id, body.action))


@router.get("/connections", response_model=Envelope[list[schemas.ConnectionOut]])
def connections(user: VerifiedUser, db: DB, user_id: str = Query("", alias="userId")):
    return ok(service.list_connections(db, user.id, user_id))


@router.get("/requests", response_model=Envelope[schemas.RequestsOut])
def requests(user: VerifiedUser, db: DB):
    return ok(service.list_requests(db, user.id))


@router.get("/suggestions", response_model=Envelope[list[schemas.SuggestionOut]])
def suggestions(user: VerifiedUser, db: DB, limit: int = Query(12, ge=1, le=100)):
    return ok(service.suggestions(db, user, limit))


@router.put("/follows/{user_id}", response_model=Envelope[None])
def follow(user_id: str, user: VerifiedUser, db: DB):
    return ok(message=service.follow(db, user, user_id, True))


@router.delete("/follows/{user_id}", response_model=Envelope[None])
def unfollow(user_id: str, user: VerifiedUser, db: DB):
    return ok(message=service.follow(db, user, user_id, False))


@router.get("/followers", response_model=Envelope[list[schemas.PersonOut]])
def followers(user: VerifiedUser, db: DB, user_id: str = Query("", alias="userId"), mode: str = "followers"):
    return ok(service.followers(db, user.id, user_id, mode))


@router.put("/blocks/{user_id}", response_model=Envelope[None])
def block(user_id: str, user: VerifiedUser, db: DB):
    return ok(message=service.block(db, user, user_id, True))


@router.delete("/blocks/{user_id}", response_model=Envelope[None])
def unblock(user_id: str, user: VerifiedUser, db: DB):
    return ok(message=service.block(db, user, user_id, False))


@router.get("/blocks", response_model=Envelope[list[schemas.BlockedOut]])
def blocks(user: VerifiedUser, db: DB):
    return ok(service.list_blocks(db, user.id))
