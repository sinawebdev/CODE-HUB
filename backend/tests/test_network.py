"""Network behavior, permission boundaries and scored suggestions."""
from sqlalchemy import event


def connect(client, requester, target, message=""):
    return client.post("/api/v1/network/connections", headers=requester.headers,
                       json={"userId": target.id, "message": message})


def requests(client, user):
    response = client.get("/api/v1/network/requests", headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_request_accept_and_remove_connection(client, make_user):
    first, second = make_user(), make_user()
    assert connect(client, first, second, "Hello").json()["message"] == "Connection request sent."
    incoming = requests(client, second)["incoming"][0]
    assert incoming["message"] == "Hello" and incoming["userId"] == first.id and incoming["mutual"] == 0
    assert requests(client, first)["outgoing"][0]["userId"] == second.id
    cid = incoming["connectionId"]
    response = client.post(f"/api/v1/network/connections/{cid}/respond", headers=second.headers,
                           json={"action": "accept"})
    assert response.json()["message"] == "Connection accepted."
    data = client.get("/api/v1/network/connections", headers=first.headers).json()["data"]
    assert data[0]["userId"] == second.id and data[0]["verified"] is False
    assert connect(client, first, second).status_code == 409
    response = client.post(f"/api/v1/network/connections/{cid}/respond", headers=first.headers,
                           json={"action": "remove"})
    assert response.json()["message"] == "Connection removed."
    assert client.get("/api/v1/network/connections", headers=first.headers).json()["data"] == []


def test_reverse_request_auto_accepts_and_pending_duplicate(client, make_user):
    first, second = make_user(), make_user()
    connect(client, first, second)
    response = connect(client, first, second)
    assert response.status_code == 409 and response.json()["detail"] == "Connection request already pending."
    assert connect(client, second, first).json()["message"] == "Connection accepted."
    assert requests(client, first) == {"incoming": [], "outgoing": []}


def test_connection_errors_and_ownership(client, make_user):
    first, second, stranger = make_user(), make_user(), make_user()
    assert connect(client, first, first).json()["detail"] == "You cannot connect with yourself."
    assert client.post("/api/v1/network/connections", headers=first.headers,
                       json={"userId": "USR-missing"}).status_code == 404
    connect(client, first, second)
    cid = requests(client, first)["outgoing"][0]["connectionId"]
    path = f"/api/v1/network/connections/{cid}/respond"
    assert client.post(path, headers=stranger.headers, json={"action": "accept"}).status_code == 403
    assert client.post(path, headers=first.headers, json={"action": "accept"}).status_code == 403
    assert client.post(path, headers=second.headers, json={"action": "remove"}).json()["detail"] == "Not connected."
    assert client.post(path, headers=second.headers, json={"action": "unknown"}).status_code == 400
    assert client.post(path, headers=second.headers, json={"action": "reject"}).json()["message"] == "Request removed."
    assert client.post(path, headers=first.headers, json={"action": "cancel"}).status_code == 404
    connect(client, first, second)
    cid = requests(client, first)["outgoing"][0]["connectionId"]
    assert client.post(f"/api/v1/network/connections/{cid}/respond", headers=first.headers,
                       json={"action": "cancel"}).status_code == 200


def test_follow_lists_unfollow_and_idempotence(client, make_user):
    first, second = make_user(), make_user()
    path = f"/api/v1/network/follows/{second.id}"
    assert client.put(path, headers=first.headers).json()["message"] == "Now following."
    assert client.put(path, headers=first.headers).json()["message"] == "Already following."
    assert client.get("/api/v1/network/followers", headers=second.headers).json()["data"][0]["userId"] == first.id
    assert client.get("/api/v1/network/followers?mode=following", headers=first.headers).json()["data"][0]["userId"] == second.id
    assert client.delete(path, headers=first.headers).json()["message"] == "Unfollowed."
    assert client.get("/api/v1/network/followers", headers=second.headers).json()["data"] == []
    assert client.put(f"/api/v1/network/follows/{first.id}", headers=first.headers).status_code == 400
    assert client.put("/api/v1/network/follows/USR-missing", headers=first.headers).status_code == 404


def test_block_removes_both_follows_connections_and_hides_suggestions(client, make_user):
    first, second = make_user(), make_user()
    connect(client, first, second)
    connect(client, second, first)
    client.put(f"/api/v1/network/follows/{second.id}", headers=first.headers)
    client.put(f"/api/v1/network/follows/{first.id}", headers=second.headers)
    path = f"/api/v1/network/blocks/{second.id}"
    assert client.put(path, headers=first.headers).json()["message"] == "User blocked."
    assert client.put(path, headers=first.headers).json()["message"] == "Already blocked."
    assert client.get("/api/v1/network/blocks", headers=first.headers).json()["data"] == [
        {"userId": second.id, "name": second.full_name}]
    for user in (first, second):
        assert client.get("/api/v1/network/connections", headers=user.headers).json()["data"] == []
        assert client.get("/api/v1/network/followers", headers=user.headers).json()["data"] == []
        assert client.get("/api/v1/network/suggestions", headers=user.headers).json()["data"] == []
    assert connect(client, second, first).json()["code"] == "BLOCKED"
    assert client.put(f"/api/v1/network/follows/{first.id}", headers=second.headers).json()["code"] == "BLOCKED"
    assert client.delete(path, headers=first.headers).json()["message"] == "User unblocked."
    assert client.get("/api/v1/network/blocks", headers=first.headers).json()["data"] == []
    assert client.put(f"/api/v1/network/blocks/{first.id}", headers=first.headers).status_code == 400


def test_suggestion_scores_exclusions_and_batched_queries(client, make_user, db):
    viewer = make_user()
    friend = make_user()
    similar = make_user()
    distant = make_user(city="Accra")
    pending = make_user()
    make_user(status="Suspended")
    connect(client, viewer, friend)
    connect(client, friend, viewer)
    connect(client, friend, similar)
    connect(client, similar, friend)
    connect(client, viewer, pending)
    for user in (viewer, similar):
        client.post("/api/v1/profiles/me/skills", headers=user.headers, json={"name": "Python"})
    queries = []
    def count_sql(*args):
        queries.append(args[2])
    event.listen(db.bind, "before_cursor_execute", count_sql)
    try:
        response = client.get("/api/v1/network/suggestions?limit=1", headers=viewer.headers)
    finally:
        event.remove(db.bind, "before_cursor_execute", count_sql)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data[0]["userId"] == similar.id and data[0]["score"] == 7 and data[0]["mutual"] == 1
    assert len(queries) <= 12
    full = client.get("/api/v1/network/suggestions", headers=viewer.headers).json()["data"]
    assert {p["userId"] for p in full} == {similar.id, distant.id}


def test_network_requires_verified_member(client, make_user):
    unverified = make_user(verified=False)
    assert client.get("/api/v1/network/requests").status_code == 401
    assert client.get("/api/v1/network/requests", headers=unverified.headers).json()["code"] == "EMAIL_NOT_VERIFIED"


def test_batched_mutual_counts_when_targets_are_already_connections(client, make_user, db):
    from app.modules.network import service
    viewer, first, second = make_user(), make_user(), make_user()
    for a, b in ((viewer, first), (viewer, second), (first, second)):
        connect(client, a, b)
        connect(client, b, a)
    assert service.mutual_counts(db, viewer.id, [first.id, second.id]) == {first.id: 1, second.id: 1}
