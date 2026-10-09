"""Company pages, workplaces, media ownership, and composition behavior."""
import pytest
from sqlalchemy import select
from app.modules.companies import service
from app.modules.companies.models import Company, CompanyLocation
from tests.conftest import PDF, upload

BASE = "/api/v1/companies"


def company(client, user, name="Acme"):
    response = client.post(BASE, headers=user.headers, json={"name": name, "industry": "Technology"})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_company_crud_listing_detail_and_promotion(client, make_user, db):
    owner, stranger = make_user(), make_user()
    row = company(client, owner)
    assert owner.role == "Employer"
    assert row["employeeCount"] == 1 and row["jobCount"] == 0
    assert row["isMember"] and row["isOwner"] and row["hq"] is None
    assert client.get(BASE).json()["data"][0]["id"] == row["id"]
    assert client.get(BASE, params={"query": "missing"}).json()["data"] == []
    assert client.get(BASE, params={"industry": "technology"}).json()["data"][0]["id"] == row["id"]
    assert client.get(BASE + "/mine", headers=owner.headers).json()["data"][0]["id"] == row["id"]
    assert client.get(BASE + "/mine", headers=stranger.headers).json()["data"] == []
    path = BASE + "/" + row["id"]
    result = client.patch(path, headers=owner.headers, json={"description": "A team", "website": "javascript:alert(1)"})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["website"] == ""
    assert client.patch(path, headers=stranger.headers, json={"name": "stolen"}).status_code == 403
    assert client.post(path + "/services", headers=owner.headers, json={"name": "Consulting"}).status_code == 201
    page = client.get(path, headers=owner.headers).json()["data"]
    assert page["canManage"] and page["members"][0]["role"] == "Owner"
    assert page["services"][0]["name"] == "Consulting"
    assert page["posts"] == [] and page["events"] == [] and page["jobs"] == []
    assert not client.get(path).json()["data"]["canManage"]
    assert service.company_stats(db) == {"companies": 1, "locations": 0}
    assert service.list_companies_admin(db)[0]["CompanyID"] == row["id"]
    assert service.set_company_verified(db, row["id"], True)
    assert service.set_company_status(db, row["id"], "Suspended")
    db.commit()
    assert client.get(BASE).json()["data"] == []
    assert not service.set_company_status(db, "CMP-missing", "Active")


def test_workplaces_hq_coordinates_photos_and_nearby(client, make_user, db):
    owner, stranger = make_user(), make_user()
    row = company(client, owner)
    path = BASE + "/" + row["id"] + "/locations"
    loc = client.post(path, headers=owner.headers, json={
        "name": "Office", "latitude": 6.09, "longitude": -0.26, "isHQ": True}).json()["data"]
    assert loc["isHQ"] and loc["photoCount"] == 0 and loc["latitude"] == 6.09
    assert "6.09%2C-0.26" in loc["mapsLink"]
    second = client.post(path, headers=owner.headers, json={"name": "Branch", "isHQ": True}).json()["data"]
    detail = client.get(BASE + "/" + row["id"]).json()["data"]
    assert detail["locationCount"] == 2 and detail["hq"]["city"] == "Koforidua"
    assert sum(x["isHQ"] for x in detail["locations"]) == 1
    nearby = client.get(BASE + "/nearby", params={"lat": 6.09, "lng": -0.26}).json()["data"]
    assert nearby[0]["distance"] == 0 and nearby[0]["nearLocation"]["id"] == loc["id"]
    update_path = BASE + "/locations/" + loc["id"]
    assert client.patch(update_path, headers=stranger.headers, json={"name": "No"}).status_code == 403
    result = client.patch(update_path, headers=owner.headers, json={"latitude": "", "longitude": None, "isHQ": True})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["latitude"] is None and result.json()["data"]["longitude"] is None
    assert db.get(CompanyLocation, loc["id"]).latitude is None
    assert client.get(BASE + "/nearby", params={"lat": 6.09, "lng": -0.26}).json()["data"] == []
    photo = upload(client, owner, "Workplace Photos")
    add = client.post(update_path + "/photos", headers=owner.headers,
                      json={"fileId": photo["fileId"], "caption": "Reception"})
    assert add.status_code == 201 and add.json()["data"]["url"] == photo["url"]
    page = client.get(BASE + "/" + row["id"]).json()["data"]
    photos = next(x["photos"] for x in page["locations"] if x["id"] == loc["id"])
    photo_path = BASE + "/location-photos/" + photos[0]["id"]
    assert client.delete(photo_path, headers=stranger.headers).status_code == 403
    assert client.delete(photo_path, headers=owner.headers).json()["message"] == "Photo deleted."
    assert client.delete(photo_path, headers=owner.headers).status_code == 404
    assert client.delete(update_path, headers=owner.headers).json()["message"] == "Workplace deleted."
    assert client.patch(update_path, headers=owner.headers, json={"name": "revive"}).status_code == 404
    assert service.company_stats(db)["locations"] == 1
    assert service.list_locations_admin(db, status="Deleted")[0]["LocationID"] == loc["id"]


def test_company_image_upload_and_file_ownership(client, make_user):
    owner, stranger = make_user(), make_user()
    row = company(client, owner)
    path = BASE + "/" + row["id"] + "/image"
    image = upload(client, owner, "Company Logos")
    response = client.put(path, headers=owner.headers, json={"kind": "logo", "fileId": image["fileId"]})
    assert response.status_code == 200 and response.json()["data"]["url"] == image["url"]
    assert client.get(BASE + "/" + row["id"]).json()["data"]["logoId"] == image["fileId"]
    stolen = upload(client, stranger, "Company Logos")
    assert client.put(path, headers=owner.headers, json={"fileId": stolen["fileId"]}).json()["code"] == "INVALID_FILE"
    wrong_folder = upload(client, owner, "Post Media")
    assert client.put(path, headers=owner.headers, json={"fileId": wrong_folder["fileId"]}).status_code == 400
    document = upload(client, owner, "Company Logos", PDF, "application/pdf", "file.pdf")
    assert client.put(path, headers=owner.headers, json={"fileId": document["fileId"]}).status_code == 400
    cover = upload(client, owner, "Company Photos")
    assert client.put(path, headers=owner.headers, json={"kind": "cover", "fileId": cover["fileId"]}).status_code == 200
    assert client.put(path, headers=stranger.headers, json={"fileId": image["fileId"]}).status_code == 403


@pytest.mark.parametrize("suffix,method,body,detail", [
    ("", "post", {}, "Company name is required."),
    ("/CMP-missing", "patch", {"name": "X"}, "Company not found."),
    ("/CMP-missing/services", "post", {"name": "X"}, "Company not found."),
    ("/CMP-missing/locations", "post", {"name": "X"}, "Company not found."),
    ("/locations/LOC-missing", "delete", None, "Workplace not found."),
])
def test_company_failures(client, make_user, suffix, method, body, detail):
    user = make_user()
    kwargs = {"headers": user.headers}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(BASE + suffix, **kwargs)
    assert response.status_code in (400, 404), response.text
    assert response.json()["detail"] == detail


def test_company_validation_permissions_and_job_counts(client, make_user):
    owner, stranger = make_user(), make_user()
    row = company(client, owner)
    path = BASE + "/" + row["id"]
    assert client.post(BASE, json={"name": "X"}).status_code == 401
    assert client.post(BASE, headers=make_user(verified=False).headers, json={"name": "X"}).status_code == 403
    assert client.post(path + "/services", headers=owner.headers, json={}).json()["detail"] == "Service name is required."
    assert client.post(path + "/locations", headers=owner.headers, json={}).json()["detail"] == "Workplace name is required."
    assert client.post(path + "/locations", headers=stranger.headers, json={"name": "X"}).status_code == 403
    assert client.post(path + "/services", headers=stranger.headers, json={"name": "X"}).status_code == 403
    assert client.get(BASE + "/nearby", params={"lat": 100, "lng": 0}).status_code == 400
    job = client.post("/api/v1/opportunities/jobs", headers=owner.headers,
                      json={"companyId": row["id"], "title": "Engineer"})
    assert job.status_code == 201, job.text
    assert client.get(BASE).json()["data"][0]["jobCount"] == 1
    assert client.get(path).json()["data"]["jobs"][0]["id"] == job.json()["data"]["id"]
    assert client.get(path).json()["data"]["jobCount"] == 1
