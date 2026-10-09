"""In-process event bus.

A module announces that something happened (e.g. OPPORTUNITY_POSTED) and other
modules react, without importing each other. Starts as plain function calls in
the same process; can be swapped for Redis/a queue later without touching modules.

Handlers run synchronously inside the caller's database transaction, each in its
own SAVEPOINT, so a failing handler is logged and rolled back without breaking the
action that published the event.
"""
import logging
from collections import defaultdict
from collections.abc import Callable

from sqlalchemy.orm import Session

logger = logging.getLogger("app.events")

Handler = Callable[..., None]
_subscribers: dict[str, list[Handler]] = defaultdict(list)

# identity
USER_REGISTERED = "identity.user_registered"  # user
EMAIL_VERIFIED = "identity.email_verified"  # user
# network
CONNECTION_REQUESTED = "network.connection_requested"  # requester, addressee_id, connection_id
CONNECTION_ACCEPTED = "network.connection_accepted"  # accepter, requester_id, connection_id
USER_FOLLOWED = "network.user_followed"  # follower, following_id
# feed
POST_REACTED = "feed.post_reacted"  # actor, post_id, post_owner_id, reaction_type
POST_COMMENTED = "feed.post_commented"  # actor, post_id, post_owner_id, comment_id
# opportunities
JOB_APPLICATION_SUBMITTED = "opportunities.job_application_submitted"  # applicant, job_id, job_title, employer_id, application_id
APPLICATION_STATUS_CHANGED = "opportunities.application_status_changed"  # actor, applicant_id, job_id, job_title, status
# messaging
MESSAGE_SENT = "messaging.message_sent"  # sender, conversation_id, recipient_ids, title, preview
# admin
VERIFICATION_REVIEWED = "admin.verification_reviewed"  # actor, user_id, status, reason


def subscribe(event_name: str) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        if handler not in _subscribers[event_name]:
            _subscribers[event_name].append(handler)
        return handler

    return register


def publish(event_name: str, db: Session, **payload) -> None:
    for handler in list(_subscribers.get(event_name, ())):
        try:
            with db.begin_nested():
                handler(db=db, **payload)
        except Exception:
            logger.exception("Event handler %s failed for %s", handler.__qualname__, event_name)
