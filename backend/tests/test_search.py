EMPTY = {"people": [], "companies": [], "jobs": [], "posts": [], "events": [], "skills": []}


def test_short_queries_return_empty_groups(client):
    assert client.get("/api/v1/search?q=a").json()["data"] == EMPTY


def test_search_finds_people_by_name_title_and_headline(client, make_user):
    viewer = make_user()
    akosua = make_user(first_name="Akosua", title="Designer")
    headline_only = make_user(first_name="Kojo", title="Accountant")
    client.patch("/api/v1/profiles/me", headers=headline_only.headers, json={"headline": "Brand strategist"})
    make_user(first_name="Akosua", last_name="Gone", status="Suspended")
    by_name = client.get("/api/v1/search?q=akos&type=people", headers=viewer.headers).json()["data"]
    assert [p["userId"] for p in by_name["people"]] == [akosua.id] and by_name["companies"] == []
    by_title = client.get("/api/v1/search?q=designer&type=people", headers=viewer.headers).json()["data"]
    assert [p["userId"] for p in by_title["people"]] == [akosua.id]
    by_headline = client.get("/api/v1/search?q=strategist", headers=viewer.headers).json()["data"]
    assert [p["userId"] for p in by_headline["people"]] == [headline_only.id]


def test_search_hides_blocked_people_and_their_posts(client, make_user):
    viewer, blocked = make_user(), make_user(first_name="Blockme")
    client.post("/api/v1/feed/posts", headers=blocked.headers, json={"content": "Blockme was here"})
    client.put(f"/api/v1/network/blocks/{blocked.id}", headers=viewer.headers)
    data = client.get("/api/v1/search?q=blockme", headers=viewer.headers).json()["data"]
    assert data["people"] == [] and data["posts"] == []
    anonymous = client.get("/api/v1/search?q=blockme").json()["data"]
    assert len(anonymous["people"]) == 1 and len(anonymous["posts"]) == 1


def test_search_across_types(client, make_user):
    owner = make_user(role="Employer")
    client.post("/api/v1/profiles/me/skills", headers=owner.headers, json={"name": "Solar Engineering"})
    company = client.post("/api/v1/companies", headers=owner.headers,
                          json={"name": "Solar Works", "industry": "Energy"}).json()["data"]
    client.post("/api/v1/opportunities/jobs", headers=owner.headers,
                json={"companyId": company["id"], "title": "Solar Technician", "description": "Install panels"})
    client.post("/api/v1/feed/posts", headers=owner.headers, json={"content": "Solar is the future"})
    client.post("/api/v1/opportunities/events", headers=owner.headers,
                json={"title": "Solar Summit", "eventDate": "2099-01-15"})
    data = client.get("/api/v1/search?q=solar", headers=owner.headers).json()["data"]
    assert [c["name"] for c in data["companies"]] == ["Solar Works"]
    assert [j["title"] for j in data["jobs"]] == ["Solar Technician"]
    assert [p["content"] for p in data["posts"]] == ["Solar is the future"]
    assert [e["title"] for e in data["events"]] == ["Solar Summit"]
    assert [s["name"] for s in data["skills"]] == ["Solar Engineering"]
    only_jobs = client.get("/api/v1/search?q=solar&type=jobs", headers=owner.headers).json()["data"]
    assert only_jobs["companies"] == [] and len(only_jobs["jobs"]) == 1
