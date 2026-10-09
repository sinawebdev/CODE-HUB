"""Messages, polling, attachments, group membership and access control."""
from tests.conftest import PDF, upload


def start(client, sender, target, message=""):
    response = client.post("/api/v1/messaging/conversations", headers=sender.headers,
                           json={"userId": target.id, "message": message})
    assert response.status_code == 200, response.text
    return response.json()["data"]["conversationId"]


def messages(client, user, cid, since=""):
    response = client.get(f"/api/v1/messaging/conversations/{cid}/messages", headers=user.headers,
                          params={"sinceId": since})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def send(client, user, cid, body="", attachment=None):
    return client.post(f"/api/v1/messaging/conversations/{cid}/messages", headers=user.headers,
                       json={"body": body, "attachment": attachment})


def test_direct_reuse_polling_read_and_notification(client, make_user):
    first, second = make_user(), make_user()
    cid = start(client, first, second, "Hello")
    conversations = client.get("/api/v1/messaging/conversations", headers=second.headers).json()["data"]
    assert conversations[0]["id"] == cid and conversations[0]["title"] == first.full_name
    assert conversations[0]["unread"] == 1 and conversations[0]["memberCount"] == 2
    assert conversations[0]["lastMessage"]["body"] == "Hello"
    first_message = messages(client, second, cid)["messages"][0]
    assert first_message["body"] == "Hello" and first_message["mine"] is False and first_message["senderName"] == first.full_name
    assert messages(client, second, cid)["conversation"]["unread"] == 0
    assert start(client, second, first, "Reply") == cid
    newest = messages(client, first, cid, first_message["id"])["messages"]
    assert len(newest) == 1 and newest[0]["body"] == "Reply"
    assert messages(client, first, cid, newest[0]["id"])["messages"] == []
    assert len(messages(client, first, cid, "MSG-missing")["messages"]) == 2
    notification = client.get("/api/v1/notifications", headers=second.headers).json()["data"]["notifications"][0]
    assert notification["title"] == f"New message from {first.full_name}"
    assert notification["body"] == "Hello" and notification["link"] == f"#/messages/{cid}"


def test_group_deduplicates_members_and_notifies_everyone(client, make_user):
    first, second, third = make_user(), make_user(), make_user()
    inactive = make_user(status="Suspended")
    response = client.post("/api/v1/messaging/conversations/group", headers=first.headers,
                           json={"memberIds": [first.id, second.id, second.id, third.id, inactive.id, "USR-missing"], "title": "Team"})
    assert response.status_code == 200, response.text
    cid = response.json()["data"]["conversationId"]
    assert send(client, first, cid, "Welcome").json()["message"] == "Sent."
    data = messages(client, second, cid)["conversation"]
    assert data["title"] == "Team" and data["type"] == "group" and data["memberCount"] == 3
    assert set(data["memberIds"]) == {first.id, second.id, third.id}
    for recipient in (second, third):
        item = client.get("/api/v1/notifications", headers=recipient.headers).json()["data"]["notifications"][0]
        assert item["title"] == "New message from Team"
    assert client.get("/api/v1/notifications", headers=first.headers).json()["data"]["notifications"] == []


def test_membership_self_missing_and_group_validation(client, make_user):
    first, second, stranger = make_user(), make_user(), make_user()
    cid = start(client, first, second)
    path = f"/api/v1/messaging/conversations/{cid}"
    assert client.get(path + "/messages", headers=stranger.headers).status_code == 403
    assert send(client, stranger, cid, "Oops").status_code == 403
    assert client.get(path + "/search?q=hello", headers=stranger.headers).status_code == 403
    assert client.patch(path + "/settings", headers=stranger.headers, json={"pinned": True}).status_code == 403
    assert client.post("/api/v1/messaging/conversations", headers=first.headers,
                       json={"userId": first.id}).json()["detail"] == "Cannot message yourself."
    assert client.post("/api/v1/messaging/conversations", headers=first.headers,
                       json={"userId": "USR-missing"}).status_code == 404
    assert client.post("/api/v1/messaging/conversations/group", headers=first.headers,
                       json={"memberIds": []}).json()["detail"] == "Select at least one member."
    assert client.post("/api/v1/messaging/conversations/group", headers=first.headers,
                       json={"memberIds": [first.id]}).json()["detail"] == "No valid members selected."
    assert send(client, first, cid, "  ").json()["detail"] == "Message cannot be empty."


def test_blocked_members_cannot_create_or_send(client, make_user):
    first, second = make_user(), make_user()
    cid = start(client, first, second)
    client.put(f"/api/v1/network/blocks/{second.id}", headers=first.headers)
    assert send(client, first, cid, "Hello").json()["code"] == "BLOCKED"
    assert send(client, second, cid, "Hello").json()["code"] == "BLOCKED"
    assert client.post("/api/v1/messaging/conversations", headers=second.headers,
                       json={"userId": first.id}).json()["code"] == "BLOCKED"
    assert client.post("/api/v1/messaging/conversations/group", headers=first.headers,
                       json={"memberIds": [second.id]}).json()["code"] == "BLOCKED"


def test_owned_attachment_signed_delivery_reply_and_delete(client, make_user):
    first, second, third = make_user(), make_user(), make_user()
    cid = start(client, first, second)
    file = upload(client, first, "Documents", content=PDF, mime="application/pdf", name="notes.pdf")
    response = send(client, first, cid, attachment={"fileId": file["fileId"], "type": "file", "url": "https://bad.example/"})
    assert response.status_code == 200, response.text
    sent = response.json()["data"]
    assert sent["attachmentUrl"].startswith(f"/api/v1/media/{file['fileId']}?token=")
    assert client.get(sent["attachmentUrl"]).status_code == 200
    assert send(client, second, cid, attachment={"fileId": file["fileId"]}).json()["code"] == "INVALID_FILE"
    wrong_folder = upload(client, first, "Profile Photos")
    assert send(client, first, cid, attachment={"fileId": wrong_folder["fileId"]}).status_code == 400
    response = send(client, second, cid, "Received", {"replyTo": sent["id"]})
    assert response.status_code == 200
    assert messages(client, first, cid)["messages"][-1]["replyTo"] == sent["id"]
    other = start(client, first, third, "Secret")
    other_id = messages(client, first, other)["messages"][0]["id"]
    assert send(client, first, cid, "Reply", {"replyTo": other_id}).status_code == 404
    path = f"/api/v1/messaging/messages/{sent['id']}"
    assert client.delete(path, headers=second.headers).status_code == 403
    assert client.delete(path, headers=first.headers).json()["message"] == "Message deleted."
    deleted = messages(client, second, cid)["messages"][0]
    assert deleted["deleted"] is True and deleted["body"] == "" and deleted["attachmentUrl"] == ""
    assert client.delete("/api/v1/messaging/messages/MSG-missing", headers=first.headers).status_code == 404


def test_reactions_search_and_settings(client, make_user):
    first, second, stranger = make_user(), make_user(), make_user()
    cid = start(client, first, second, "Project Hello")
    mid = messages(client, first, cid)["messages"][0]["id"]
    path = f"/api/v1/messaging/messages/{mid}/reactions"
    assert client.post(path, headers=stranger.headers, json={"type": "love"}).status_code == 403
    assert client.post(path, headers=second.headers, json={"type": "love"}).json()["message"] == "Reaction added."
    assert client.post(path, headers=second.headers, json={"type": "wow"}).json()["message"] == "Reaction updated."
    assert messages(client, first, cid)["messages"][0]["reactions"] == [{"userId": second.id, "type": "wow"}]
    assert client.post(path, headers=second.headers, json={"type": "wow"}).json()["data"] == {"removed": True}
    assert client.post(path, headers=second.headers, json={"type": "invalid"}).status_code == 200
    assert messages(client, first, cid)["messages"][0]["reactions"][0]["type"] == "like"
    assert client.post("/api/v1/messaging/messages/MSG-missing/reactions", headers=first.headers,
                       json={"type": "love"}).status_code == 404
    search = f"/api/v1/messaging/conversations/{cid}/search"
    assert client.get(search + "?q=hELLo", headers=first.headers).json()["data"][0]["id"] == mid
    assert client.get(search, headers=first.headers).json()["data"] == []
    settings = f"/api/v1/messaging/conversations/{cid}/settings"
    assert client.patch(settings, headers=first.headers, json={"pinned": True, "muted": True}).json()["message"] == "Updated."
    conv = messages(client, first, cid)["conversation"]
    assert conv["pinned"] is True and conv["muted"] is True
    assert messages(client, second, cid)["conversation"]["pinned"] is False
    assert client.patch(settings, headers=first.headers, json={}).json()["detail"] == "Unknown flag."
    client.delete(f"/api/v1/messaging/messages/{mid}", headers=first.headers)
    assert client.get(search + "?q=hello", headers=first.headers).json()["data"] == []


def test_messaging_requires_verified_member(client, make_user):
    assert client.get("/api/v1/messaging/conversations").status_code == 401
    user = make_user(verified=False)
    assert client.get("/api/v1/messaging/conversations", headers=user.headers).status_code == 403
