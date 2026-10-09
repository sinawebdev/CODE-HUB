from datetime import timedelta

from app.core.utils import utcnow
from app.modules.stories.models import Story
from app.modules.stories.service import cleanup_expired_stories
from tests.conftest import upload


def create(client, user):
    media = upload(client, user, "Stories")
    response = client.post("/api/v1/stories", headers=user.headers,
                           json={"fileId": media["fileId"], "caption": "A day in Koforidua"})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_story_media_permissions_and_shape(client, make_user):
    owner, other = make_user(), make_user()
    story = create(client, owner)
    assert story["isMine"] and not story["viewed"] and story["viewCount"] == 0
    assert story["url"] == f"/api/v1/media/{story['fileId']}" and story["user"]["userId"] == owner.id
    assert client.post("/api/v1/stories", headers=other.headers,
                       json={"fileId": story["fileId"]}).status_code == 400
    media = upload(client, owner, "Post Media")
    assert client.post("/api/v1/stories", headers=owner.headers,
                       json={"fileId": media["fileId"]}).status_code == 400
    assert client.delete(f"/api/v1/stories/{story['id']}", headers=other.headers).status_code == 403


def test_unique_views_and_group_order(client, make_user):
    viewer, author, third = make_user(), make_user(), make_user()
    their_story, new_story, mine = create(client, author), create(client, third), create(client, viewer)
    target = f"/api/v1/stories/{their_story['id']}/view"
    assert client.post(target, headers=author.headers).json()["data"]["viewCount"] == 0
    assert client.post(target, headers=viewer.headers).json()["data"]["viewCount"] == 1
    assert client.post(target, headers=viewer.headers).json()["data"]["viewCount"] == 1
    groups = client.get("/api/v1/stories", headers=viewer.headers).json()["data"]
    assert [g["userId"] for g in groups] == [viewer.id, third.id, author.id]
    assert groups[-1]["stories"][0]["viewed"] and not groups[-1]["hasUnviewed"]


def test_expired_deleted_blocked_stories_and_maintenance(client, make_user, db):
    viewer, author, staff = make_user(), make_user(), make_user(role="Moderator")
    expired = create(client, author)
    db.get(Story, expired["id"]).expires_at = utcnow() - timedelta(hours=1)
    db.commit()
    assert client.get("/api/v1/stories").json()["data"] == []
    assert client.post(f"/api/v1/stories/{expired['id']}/view", headers=viewer.headers).status_code == 404
    assert cleanup_expired_stories(db) == 1 and cleanup_expired_stories(db) == 0
    assert db.get(Story, expired["id"]).status == "Expired"
    fresh = create(client, author)
    client.put(f"/api/v1/network/blocks/{author.id}", headers=viewer.headers)
    assert client.get("/api/v1/stories", headers=viewer.headers).json()["data"] == []
    assert len(client.get("/api/v1/stories").json()["data"]) == 1
    assert client.delete(f"/api/v1/stories/{fresh['id']}", headers=staff.headers).status_code == 200
    assert client.get("/api/v1/stories").json()["data"] == []
