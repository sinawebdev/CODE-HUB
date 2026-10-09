from tests.conftest import upload


def test_my_profile_and_update(client, make_user):
    user = make_user(first_name="Akosua", last_name="Adjei", title="Designer")
    page = client.get("/api/v1/profiles/me", headers=user.headers).json()["data"]
    assert page["restricted"] is False and page["user"]["FullName"] == "Akosua Adjei"
    assert page["profile"]["Headline"] == "Designer" and page["relationship"] is None
    assert page["stats"] == {"connections": 0, "followers": 0, "following": 0, "posts": 0}
    response = client.patch("/api/v1/profiles/me", headers=user.headers, json={
        "headline": "Brand designer", "about": "I design.", "city": "Accra", "website": "javascript:alert(1)",
        "profileVisibility": "Nonsense", "firstName": "Akos",
    })
    assert response.status_code == 200 and response.json()["message"] == "Profile updated."
    updated = response.json()["data"]
    assert updated["profile"]["Headline"] == "Brand designer" and updated["profile"]["City"] == "Accra"
    assert updated["profile"]["Website"] == "" and updated["profile"]["Visibility"] == "Public"
    assert updated["user"]["FirstName"] == "Akos" and updated["user"]["City"] == "Accra"


def test_profile_items_and_completion(client, make_user):
    user = make_user()
    h = user.headers
    assert client.post("/api/v1/profiles/me/skills", headers=h, json={"name": "Figma"}).status_code == 201
    dup = client.post("/api/v1/profiles/me/skills", headers=h, json={"name": "figma"})
    assert dup.status_code == 409 and dup.json()["detail"] == "You already have this skill."
    assert client.post("/api/v1/profiles/me/experience", headers=h, json={"title": "Dev"}).json()["detail"] == \
        "Title and company are required."
    assert client.post("/api/v1/profiles/me/experience", headers=h,
                       json={"title": "Dev", "company": "Hub", "startDate": "2021-01", "current": True}).status_code == 201
    assert client.post("/api/v1/profiles/me/education", headers=h, json={}).json()["detail"] == "School is required."
    assert client.post("/api/v1/profiles/me/education", headers=h, json={"school": "KTU"}).status_code == 201
    assert client.post("/api/v1/profiles/me/certifications", headers=h,
                       json={"name": "AWS", "credentialUrl": "ftp://x"}).status_code == 201
    assert client.post("/api/v1/profiles/me/projects", headers=h, json={"title": "App"}).status_code == 201
    page = client.get("/api/v1/profiles/me", headers=h).json()["data"]
    assert [s["name"] for s in page["skills"]] == ["Figma"]
    assert page["experience"][0]["current"] is True and page["certifications"][0]["url"] == ""
    assert page["profile"]["CompletionPct"] == 60  # name, headline, city, skills, experience, education = 6/10
    for kind, key in (("experience", "experience"), ("education", "education"),
                      ("certifications", "certifications"), ("projects", "projects")):
        item_id = page[key][0]["id"]
        assert client.delete(f"/api/v1/profiles/me/{kind}/{item_id}", headers=h).status_code == 200
    skill_id = page["skills"][0]["id"]
    other = make_user()
    assert client.delete(f"/api/v1/profiles/me/skills/{skill_id}", headers=other.headers).status_code == 404
    assert client.delete(f"/api/v1/profiles/me/skills/{skill_id}", headers=h).status_code == 200


def test_photo_upload_must_be_own_file_in_right_folder(client, make_user):
    user, other = make_user(), make_user()
    photo = upload(client, user, "Profile Photos")
    ok = client.put("/api/v1/profiles/me/photo", headers=user.headers, json={"kind": "profile", "fileId": photo["fileId"]})
    assert ok.json()["data"]["url"] == photo["url"]
    stolen = client.put("/api/v1/profiles/me/photo", headers=other.headers, json={"kind": "profile", "fileId": photo["fileId"]})
    assert stolen.status_code == 400
    wrong_folder = client.put("/api/v1/profiles/me/photo", headers=user.headers, json={"kind": "cover", "fileId": photo["fileId"]})
    assert wrong_folder.status_code == 400


def test_visibility_rules(client, make_user, db):
    owner, viewer, staff = make_user(), make_user(), make_user(role="Moderator")
    client.patch("/api/v1/profiles/me", headers=owner.headers, json={"profileVisibility": "Connections",
                                                                     "contactVisibility": "Private"})
    hidden = client.get(f"/api/v1/profiles/{owner.id}", headers=viewer.headers).json()["data"]
    assert hidden["restricted"] is True and hidden["message"] == "This profile is private."
    seen_by_staff = client.get(f"/api/v1/profiles/{owner.id}", headers=staff.headers).json()["data"]
    assert seen_by_staff["restricted"] is False
    from app.modules.network.models import Connection
    db.add(Connection(requester_id=viewer.id, addressee_id=owner.id, status="Accepted"))
    db.commit()
    connected = client.get(f"/api/v1/profiles/{owner.id}", headers=viewer.headers).json()["data"]
    assert connected["restricted"] is False and connected["profile"]["ContactEmail"] == ""
    assert connected["relationship"]["connected"] is True and connected["user"]["Email"] is None
    assert connected["stats"]["connections"] == 1


def test_suspended_profiles_are_hidden(client, make_user):
    viewer = make_user()
    gone = make_user(status="Suspended")
    assert client.get(f"/api/v1/profiles/{gone.id}", headers=viewer.headers).status_code == 404
    assert client.get("/api/v1/profiles/USR-missing", headers=viewer.headers).status_code == 404
