from app.core import email as email_module


def _company(client, owner, name="Acme Ltd"):
    response = client.post("/api/v1/companies", headers=owner.headers, json={"name": name, "industry": "IT"})
    assert response.status_code in (200, 201), response.text
    return response.json()["data"]


def _post(client, user, content="Hello Koforidua"):
    response = client.post("/api/v1/feed/posts", headers=user.headers, json={"content": content})
    assert response.status_code in (200, 201), response.text
    return response.json()["data"]


def test_staff_only_and_admin_only_endpoints(client, make_user):
    member, moderator, admin = make_user(), make_user(role="Moderator"), make_user(role="Admin")
    assert client.get("/api/v1/admin/stats", headers=member.headers).status_code == 403
    assert client.get("/api/v1/admin/stats", headers=moderator.headers).status_code == 200
    assert client.get("/api/v1/admin/settings", headers=moderator.headers).status_code == 403
    assert client.get("/api/v1/admin/settings", headers=admin.headers).status_code == 200


def test_stats_shape(client, make_user):
    admin = make_user(role="Admin")
    _post(client, admin)
    stats = client.get("/api/v1/admin/stats", headers=admin.headers).json()["data"]
    assert stats["totalUsers"] == 1 and stats["posts"] == 1 and stats["unverifiedEmails"] == 0
    assert len(stats["signupTrend"]) == 7 and len(stats["postTrend"]) == 7
    assert {r["label"] for r in stats["roleBreakdown"]} >= {"Admin", "Professional"}


def test_resource_lists_hide_secrets_and_filter(client, make_user):
    admin = make_user(role="Admin", first_name="Zed")
    make_user(first_name="Yaw")
    rows = client.get("/api/v1/admin/resources/users", headers=admin.headers).json()["data"]
    assert len(rows) == 2 and list(rows[0])[:6] == ["UserID", "FirstName", "LastName", "Email", "Phone", "Role"]
    assert all("PasswordHash" not in r and "password_hash" not in r for r in rows)
    found = client.get("/api/v1/admin/resources/users?query=yaw", headers=admin.headers).json()["data"]
    assert [r["FirstName"] for r in found] == ["Yaw"]
    for resource in ("companies", "jobs", "posts", "reports", "events", "locations", "verification",
                     "applications", "auditlogs"):
        response = client.get(f"/api/v1/admin/resources/{resource}", headers=admin.headers)
        assert response.status_code == 200, (resource, response.text)
    assert client.get("/api/v1/admin/resources/secrets", headers=admin.headers).json()["detail"] == "Unknown resource."


def test_user_role_and_status_rules(client, make_user):
    admin, target, boss = make_user(role="Admin"), make_user(), make_user(role="Super Admin")
    url = f"/api/v1/admin/users/{target.id}"
    assert client.put(f"{url}/role", headers=admin.headers, json={"role": "Moderator"}).status_code == 200
    assert client.get(url, headers=admin.headers).json()["data"]["Role"] == "Moderator"
    denied = client.put(f"{url}/role", headers=admin.headers, json={"role": "Super Admin"})
    assert denied.json()["detail"] == "Only a Super Admin can assign Super Admin."
    assert client.put(f"/api/v1/admin/users/{boss.id}/status", headers=admin.headers,
                      json={"status": "Suspended"}).json()["detail"] == "Only a Super Admin can modify a Super Admin."
    assert client.put(f"/api/v1/admin/users/{admin.id}/status", headers=admin.headers,
                      json={"status": "Disabled"}).json()["detail"] == "You cannot change your own status."
    assert client.put(f"/api/v1/admin/users/{boss.id}/role", headers=boss.headers,
                      json={"role": "Admin"}).json()["detail"] == "You are the last Super Admin. Promote another user first."
    old_headers = target.headers
    assert client.put(f"{url}/status", headers=admin.headers, json={"status": "Suspended"}).status_code == 200
    assert client.get("/api/v1/auth/session", headers=old_headers).status_code == 401  # signed out everywhere


def test_moderation_delete_and_restore(client, make_user):
    admin, author = make_user(role="Admin"), make_user()
    post = _post(client, author)
    removed = client.delete(f"/api/v1/admin/resources/posts/{post['id']}", headers=admin.headers)
    assert removed.json()["message"] == "Post removed."
    assert client.get(f"/api/v1/feed/posts/{post['id']}", headers=author.headers).status_code == 404
    assert client.post(f"/api/v1/admin/resources/posts/{post['id']}/restore", headers=admin.headers).status_code == 200
    assert client.get(f"/api/v1/feed/posts/{post['id']}", headers=author.headers).status_code == 200
    company = _company(client, author)
    assert client.delete(f"/api/v1/admin/resources/companies/{company['id']}", headers=admin.headers).json()["message"] == \
        "Company suspended."
    assert client.delete("/api/v1/admin/resources/posts/POST-missing", headers=admin.headers).status_code == 404
    audit = client.get("/api/v1/admin/resources/auditlogs", headers=admin.headers).json()["data"]
    assert {"ADMIN_DELETE", "ADMIN_RESTORE", "ADMIN_SUSPEND_COMPANY"} <= {row["Action"] for row in audit}


def test_reports_flow(client, make_user):
    reporter, staff = make_user(), make_user(role="Moderator")
    body = {"targetType": "Post", "targetId": "POST-1", "reason": "Spam", "details": "ads"}
    assert client.post("/api/v1/reports", headers=reporter.headers, json=body).status_code == 201
    assert client.post("/api/v1/reports", headers=reporter.headers, json=body).json()["detail"] == "You already reported this."
    assert client.post("/api/v1/reports", headers=reporter.headers,
                       json={**body, "targetType": "Planet"}).json()["detail"] == "Invalid report target."
    report = client.get("/api/v1/admin/resources/reports", headers=staff.headers).json()["data"][0]
    reviewed = client.patch(f"/api/v1/admin/reports/{report['ReportID']}", headers=staff.headers,
                            json={"status": "Resolved", "note": "removed"})
    assert reviewed.status_code == 200
    report = client.get("/api/v1/admin/resources/reports", headers=staff.headers).json()["data"][0]
    assert report["Status"] == "Resolved" and report["Details"] == "ads | Note: removed"


def test_verification_center(client, make_user, db):
    from app.core.config import settings  # noqa: F401  (settings unchanged; emails go to the dev outbox)

    member, owner, admin = make_user(), make_user(), make_user(role="Admin")
    assert client.post("/api/v1/verification-requests", headers=member.headers, json={"type": "user", "note": "me"}).status_code == 201
    assert client.post("/api/v1/verification-requests", headers=member.headers,
                       json={"type": "user"}).json()["detail"] == "You already have a pending request."
    company = _company(client, owner)
    assert client.post("/api/v1/verification-requests", headers=member.headers,
                       json={"type": "company", "companyId": company["id"]}).json()["detail"] == "Not allowed."
    assert client.post("/api/v1/verification-requests", headers=owner.headers,
                       json={"type": "company", "companyId": company["id"]}).status_code == 201
    pending = client.get("/api/v1/admin/verifications?status=Pending", headers=admin.headers).json()["data"]
    assert len(pending) == 2
    by_type = {v["type"]: v for v in pending}
    assert by_type["company"]["companyName"] == "Acme Ltd" and by_type["user"]["userEmail"] == member.email
    no_reason = client.post(f"/api/v1/admin/verifications/{by_type['user']['id']}/review", headers=admin.headers,
                            json={"decision": "reject"})
    assert no_reason.json()["detail"] == "A rejection reason is required."
    email_module.OUTBOX.clear()
    client.post(f"/api/v1/admin/verifications/{by_type['user']['id']}/review", headers=admin.headers,
                json={"decision": "approve"})
    client.post(f"/api/v1/admin/verifications/{by_type['company']['id']}/review", headers=admin.headers,
                json={"decision": "reject", "reason": "Blurry documents"})
    assert client.get("/api/v1/auth/session", headers=member.headers).json()["data"]["user"]["Verified"] is True
    assert client.get(f"/api/v1/companies/{company['id']}", headers=owner.headers).json()["data"]["verified"] is False
    assert [m["subject"] for m in email_module.OUTBOX] == [
        "Your KoforLink verification was approved", "Update regarding your KoforLink verification"]
    assert "Blurry documents" in email_module.OUTBOX[-1]["html"]
    notes = client.get("/api/v1/notifications", headers=member.headers).json()["data"]["notifications"]
    assert notes[0]["title"] == "Verification approved"


def test_settings_roundtrip(client, make_user):
    admin = make_user(role="Admin")
    saved = client.put("/api/v1/admin/settings", headers=admin.headers, json={
        "platformName": "KoforLink Beta", "primaryColor": "not-a-colour", "maintenanceMode": True,
        "registrationEnabled": "FALSE"})
    assert saved.status_code == 200 and saved.json()["message"] == "Settings saved."
    current = client.get("/api/v1/admin/settings", headers=admin.headers).json()["data"]
    assert current["platformName"] == "KoforLink Beta" and current["primaryColor"] == "#0E7C4A"
    assert current["maintenanceMode"] == "TRUE" and current["registrationEnabled"] == "FALSE"
