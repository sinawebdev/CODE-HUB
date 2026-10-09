from tests.conftest import set_setting


def test_bootstrap_anonymous(client):
    data = client.get("/api/v1/platform/bootstrap").json()["data"]
    assert data["authenticated"] is False and data["user"] is None
    assert data["settings"]["registrationEnabled"] == "TRUE" and data["settings"]["defaultCity"] == "Koforidua"
    assert data["app"]["name"] == "KoforLink"


def test_bootstrap_signed_in(client, make_user):
    user = make_user(role="Moderator")
    data = client.get("/api/v1/platform/bootstrap", headers=user.headers).json()["data"]
    assert data["authenticated"] is True and data["user"]["UserID"] == user.id
    assert data["counts"] == {"notifications": 0, "messages": 0, "connectionRequests": 0}
    assert data["isStaff"] is True and data["isAdmin"] is False and data["emailVerified"] is True


def test_maintenance_mode_blocks_members_but_not_staff(client, make_user, db):
    member, staff = make_user(), make_user(role="Admin")
    set_setting(db, "maintenanceMode", "TRUE")
    blocked = client.get("/api/v1/profiles/me", headers=member.headers)
    assert blocked.status_code == 503 and blocked.json()["code"] == "MAINTENANCE"
    assert client.get("/api/v1/profiles/me", headers=staff.headers).status_code == 200
    assert client.get("/api/v1/platform/bootstrap", headers=member.headers).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": member.email, "password": member.password})
    assert login.json()["code"] == "MAINTENANCE"
