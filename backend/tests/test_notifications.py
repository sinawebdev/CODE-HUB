"""Notification ownership and event bus integration."""
import pytest
from app.core import events


def notifications(client, user, limit=50):
    response = client.get(f"/api/v1/notifications?limit={limit}", headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_network_notifications_read_delete_and_ownership(client, make_user):
    first, second = make_user(), make_user()
    client.post("/api/v1/network/connections", headers=first.headers, json={"userId": second.id})
    client.put(f"/api/v1/network/follows/{second.id}", headers=first.headers)
    data = notifications(client, second, 1)
    assert len(data["notifications"]) == 1 and data["unread"] == 2
    item = data["notifications"][0]
    assert item["title"] == "New follower" and item["body"] == f"{first.full_name} started following you."
    assert item["link"] == "#/network" and item["actorPhoto"] == "" and item["read"] is False
    path = f"/api/v1/notifications/{item['id']}"
    assert client.post(path + "/read", headers=first.headers).status_code == 404
    assert client.delete(path, headers=first.headers).status_code == 404
    assert client.post(path + "/read", headers=second.headers).json()["message"] == "Marked read."
    assert notifications(client, second)["unread"] == 1
    assert client.post("/api/v1/notifications/read-all", headers=second.headers).json()["message"] == "All marked read."
    assert notifications(client, second)["unread"] == 0
    assert client.delete(path, headers=second.headers).json()["message"] == "Notification deleted."
    assert len(notifications(client, second)["notifications"]) == 1
    assert client.delete("/api/v1/notifications/NTF-missing", headers=second.headers).status_code == 404


@pytest.mark.parametrize("event_name,kind,title,body,link,payload", [
    (events.POST_REACTED, "reaction", "New reaction", "{name} reacted to your post.", "#/post/P",
     {"post_id": "P", "reaction_type": "love"}),
    (events.POST_COMMENTED, "comment", "New comment", "{name} commented on your post.", "#/post/P",
     {"post_id": "P", "comment_id": "C"}),
    (events.JOB_APPLICATION_SUBMITTED, "job_application", "New job application", "{name} applied for Designer.", "#/job/J",
     {"job_id": "J", "job_title": "Designer", "application_id": "A"}),
    (events.APPLICATION_STATUS_CHANGED, "application_status", "Application update",
     "Your application for Designer is now: Interview.", "#/job/J",
     {"job_id": "J", "job_title": "Designer", "status": "Interview"}),
    (events.VERIFICATION_REVIEWED, "verification", "Verification rejected",
     "Your verification request has been rejected. Reason: Missing document", "#/settings",
     {"status": "Rejected", "reason": "Missing document"}),
])
def test_event_texts_and_skip_self(client, make_user, db, event_name, kind, title, body, link, payload):
    actor, recipient = make_user(), make_user()
    payload = dict(payload)
    actor_key = "applicant" if event_name == events.JOB_APPLICATION_SUBMITTED else "actor"
    recipient_key = {events.POST_REACTED: "post_owner_id", events.POST_COMMENTED: "post_owner_id",
                     events.JOB_APPLICATION_SUBMITTED: "employer_id", events.APPLICATION_STATUS_CHANGED: "applicant_id",
                     events.VERIFICATION_REVIEWED: "user_id"}[event_name]
    payload.update({actor_key: actor, recipient_key: recipient.id})
    events.publish(event_name, db, **payload)
    db.commit()
    item = notifications(client, recipient)["notifications"][0]
    assert (item["type"], item["title"], item["body"], item["link"]) == (
        kind, title, body.format(name=actor.full_name), link)
    payload[recipient_key] = actor.id
    events.publish(event_name, db, **payload)
    db.commit()
    assert notifications(client, actor)["notifications"] == []


def test_email_verified_welcome_has_no_actor(client, make_user, db):
    user = make_user()
    events.publish(events.EMAIL_VERIFIED, db, user=user)
    db.commit()
    item = notifications(client, user)["notifications"][0]
    assert item["title"] == "Welcome to KoforLink" and item["actorPhoto"] == ""
    assert item["body"] == "Your email is verified. Complete your profile to get discovered."
    assert item["link"] == "#/profile"


def test_connection_acceptance_notification(client, make_user):
    first, second = make_user(), make_user()
    client.post("/api/v1/network/connections", headers=first.headers, json={"userId": second.id})
    client.post("/api/v1/network/connections", headers=second.headers, json={"userId": first.id})
    item = notifications(client, first)["notifications"][0]
    assert item["type"] == "connection_accepted"
    assert item["body"] == f"{second.full_name} accepted your connection request."


def test_notification_auth(client, make_user):
    assert client.get("/api/v1/notifications").status_code == 401
    user = make_user(verified=False)
    assert client.get("/api/v1/notifications", headers=user.headers).status_code == 403
