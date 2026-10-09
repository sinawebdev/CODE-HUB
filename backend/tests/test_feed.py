from app.modules.feed.models import Post
from tests.conftest import upload


def publish(client, user, **body):
    response = client.post("/api/v1/feed/posts", headers=user.headers, json={"content": "Hello Koforidua", **body})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_publish_media_ownership_and_permissions(client, make_user):
    owner, other = make_user(), make_user()
    media = upload(client, owner)
    post = publish(client, owner, media=[{"fileId": media["fileId"], "type": "image"}])
    assert post["author"]["userId"] == owner.id and post["isMine"]
    assert post["mediaUrl"] == media["url"] and post["media"][0]["fileId"] == media["fileId"]
    denied = client.post("/api/v1/feed/posts", headers=other.headers,
                         json={"media": [{"fileId": media["fileId"]}]})
    assert denied.status_code == 400 and denied.json()["code"] == "INVALID_FILE"
    assert client.patch(f"/api/v1/feed/posts/{post['id']}", headers=other.headers,
                        json={"content": "hijacked"}).status_code == 403
    assert client.post("/api/v1/feed/posts", headers=owner.headers, json={}).status_code == 400
    long_post = client.post("/api/v1/feed/posts", headers=owner.headers, json={"content": "x" * 5001})
    assert long_post.status_code == 400 and long_post.json()["detail"] == "Post is too long."
    assert client.post("/api/v1/feed/posts", json={"content": "anonymous"}).status_code == 401
    unverified = make_user(verified=False)
    assert client.post("/api/v1/feed/posts", headers=unverified.headers,
                       json={"content": "unverified"}).status_code == 403


def test_reactions_toggle_change_and_counter(client, make_user, db):
    owner, reactor = make_user(), make_user()
    post = publish(client, owner)
    url = f"/api/v1/feed/posts/{post['id']}/reactions"
    assert client.post(url, headers=reactor.headers, json={"type": "love"}).json()["data"] == {
        "liked": True, "count": 1, "type": "love"}
    assert client.post(url, headers=reactor.headers, json={"type": "support"}).json()["message"] == "Reaction updated."
    assert client.post(url, headers=reactor.headers, json={"type": "support"}).json()["data"] == {
        "liked": False, "count": 0, "type": ""}
    assert db.get(Post, post["id"]).like_count == 0


def test_comments_parent_and_idempotent_delete(client, make_user):
    owner, other, staff = make_user(), make_user(), make_user(role="Moderator")
    post = publish(client, owner)
    other_post = publish(client, other)
    url = f"/api/v1/feed/posts/{post['id']}/comments"
    comment = client.post(url, headers=other.headers, json={"content": "Nice work"}).json()["data"]
    assert comment["parentId"] == "" and comment["author"]["userId"] == other.id
    assert client.get(url, headers=staff.headers).json()["data"][0]["isMine"]
    assert client.post(f"/api/v1/feed/posts/{other_post['id']}/comments", headers=owner.headers,
                       json={"content": "reply", "parentId": comment["id"]}).status_code == 400
    target = f"/api/v1/feed/comments/{comment['id']}"
    assert client.delete(target, headers=owner.headers).status_code == 403
    assert client.delete(target, headers=staff.headers).status_code == 200
    assert client.delete(target, headers=staff.headers).status_code == 200
    assert client.get(url).json()["data"] == []
    assert client.get(f"/api/v1/feed/posts/{post['id']}").json()["data"]["commentCount"] == 0


def test_saves_share_repost_views_and_moderation(client, make_user):
    author, user, staff = make_user(), make_user(), make_user(role="Moderator")
    post = publish(client, author)
    base = f"/api/v1/feed/posts/{post['id']}"
    assert client.get(base).json()["data"]["viewCount"] == 1
    assert client.put(f"{base}/save", headers=user.headers).json()["message"] == "Post saved."
    assert client.put(f"{base}/save", headers=user.headers).json()["message"] == "Already saved."
    assert client.get("/api/v1/feed/posts/saved", headers=user.headers).json()["data"][0]["saved"]
    assert client.post(f"{base}/share", headers=user.headers).json()["data"]["url"] == f"#/post/{post['id']}"
    repost = publish(client, user, repostOf=post["id"])
    assert repost["repostOf"]["shareCount"] == 2
    assert client.delete(base, headers=user.headers).status_code == 403
    assert client.delete(base, headers=staff.headers).status_code == 200
    assert client.get(base).status_code == 404
    assert client.get("/api/v1/feed/posts/saved", headers=user.headers).json()["data"] == []


def test_blocking_hides_feed_trending_saved_user_posts_and_reposts(client, make_user):
    viewer, author = make_user(), make_user()
    post = publish(client, author, content="Discover local designers")
    publish(client, viewer, repostOf=post["id"])
    client.put(f"/api/v1/feed/posts/{post['id']}/save", headers=viewer.headers)
    client.put(f"/api/v1/network/blocks/{author.id}", headers=viewer.headers)
    feed = client.get("/api/v1/feed", headers=viewer.headers).json()["data"]
    assert len(feed["posts"]) == 1 and feed["posts"][0]["repostOf"] is None
    assert client.get(f"/api/v1/feed/posts?userId={author.id}", headers=viewer.headers).json()["data"] == []
    assert client.get("/api/v1/feed/posts/saved", headers=viewer.headers).json()["data"] == []
    assert client.get(f"/api/v1/feed/posts/{post['id']}", headers=viewer.headers).status_code == 404
    assert all(p["author"]["userId"] != author.id for p in
               client.get("/api/v1/feed/trending", headers=viewer.headers).json()["data"]["posts"])


def test_company_post_requires_manager(client, make_user):
    owner, stranger = make_user(), make_user()
    company = client.post("/api/v1/companies", headers=owner.headers,
                          json={"name": "Acme", "industry": "IT"}).json()["data"]
    response = client.post("/api/v1/feed/posts", headers=stranger.headers,
                           json={"content": "Fake announcement", "companyId": company["id"]})
    assert response.status_code == 403 and response.json()["detail"] == "Not allowed for this company."
    assert publish(client, owner, companyId=company["id"])["company"]["id"] == company["id"]


def test_feed_pagination_and_skill_affinity(client, make_user):
    viewer, stranger = make_user(city="Accra"), make_user(city="Tamale")
    client.post("/api/v1/profiles/me/skills", headers=viewer.headers, json={"name": "Python"})
    publish(client, stranger, content="No matching skill")
    relevant = publish(client, stranger, content="Python opportunities")
    page = client.get("/api/v1/feed?limit=1", headers=viewer.headers).json()["data"]
    assert page["posts"][0]["id"] == relevant["id"] and page["hasMore"]
    assert not client.get("/api/v1/feed?limit=1&offset=1", headers=viewer.headers).json()["data"]["hasMore"]
    assert client.get("/api/v1/feed/trending").json()["data"]["skills"] == [{"name": "Python", "count": 1}]
