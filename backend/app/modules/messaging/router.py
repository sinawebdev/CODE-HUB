"""Direct and group messaging over polling HTTP endpoints."""
from fastapi import APIRouter, Query
from app.core.database import DB
from app.core.permissions import VerifiedUser
from app.core.schemas import Envelope, ok
from app.modules.messaging import schemas, service

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.post("/conversations", response_model=Envelope[schemas.StartedOut])
def start(body: schemas.StartIn, user: VerifiedUser, db: DB):
    data, message = service.start_conversation(db, user, body.user_id, body.message)
    return ok(data, message)


@router.post("/conversations/group", response_model=Envelope[schemas.StartedOut])
def group(body: schemas.GroupIn, user: VerifiedUser, db: DB):
    return ok(service.create_group(db, user, body.member_ids, body.title), "Group created.")


@router.get("/conversations", response_model=Envelope[list[schemas.ConversationOut]])
def conversations(user: VerifiedUser, db: DB):
    return ok(service.list_conversations(db, user.id))


@router.get("/conversations/{conversation_id}/messages", response_model=Envelope[schemas.MessagesOut])
def messages(conversation_id: str, user: VerifiedUser, db: DB, since_id: str = Query("", alias="sinceId")):
    return ok(service.get_messages(db, user.id, conversation_id, since_id))


@router.post("/conversations/{conversation_id}/messages", response_model=Envelope[schemas.SentOut])
def send(conversation_id: str, body: schemas.MessageIn, user: VerifiedUser, db: DB):
    attachment = body.attachment.model_dump() if body.attachment else None
    return ok(service.send_message(db, user, conversation_id, body.body, attachment), "Sent.")


@router.delete("/messages/{message_id}", response_model=Envelope[None])
def delete(message_id: str, user: VerifiedUser, db: DB):
    service.delete_message(db, user, message_id)
    return ok(message="Message deleted.")


@router.post("/messages/{message_id}/reactions", response_model=Envelope[schemas.RemovedOut])
def react(message_id: str, body: schemas.ReactionIn, user: VerifiedUser, db: DB):
    data, message = service.react_message(db, user, message_id, body.type)
    return ok(data, message)


@router.get("/conversations/{conversation_id}/search", response_model=Envelope[list[schemas.SearchOut]])
def search(conversation_id: str, user: VerifiedUser, db: DB, q: str = Query("", max_length=100)):
    return ok(service.search_messages(db, user.id, conversation_id, q))


@router.patch("/conversations/{conversation_id}/settings", response_model=Envelope[None])
def settings(conversation_id: str, body: schemas.SettingsIn, user: VerifiedUser, db: DB):
    service.set_settings(db, user.id, conversation_id, body.model_dump(exclude_unset=True))
    return ok(message="Updated.")
