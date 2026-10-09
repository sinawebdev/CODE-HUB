"""Jobs, application workflow, private CVs, events, and registration."""
from datetime import timedelta
import pytest
from app.core import email
from app.core.utils import utcnow
from app.modules.opportunities import service
from app.modules.opportunities.models import Event, Job, JobAlert, JobSkill
from sqlalchemy import select
from tests.conftest import PDF, set_setting, upload

BASE = "/api/v1/opportunities"


def setup_job(client, make_user, **fields):
    owner = make_user()
    company = client.post("/api/v1/companies", headers=owner.headers, json={"name": "Acme"}).json()["data"]
    location = client.post("/api/v1/companies/" + company["id"] + "/locations", headers=owner.headers,
                           json={"name": "HQ", "latitude": 6.09, "longitude": -0.26}).json()["data"]
    response = client.post(BASE + "/jobs", headers=owner.headers, json={
        "title": "Engineer", "companyId": company["id"], "locationId": location["id"],
        "skills": "Python, Design", **fields})
    assert response.status_code == 201, response.text
    return owner, company, response.json()["data"]


def tomorrow():
    return (utcnow().date() + timedelta(days=1)).isoformat()


def test_job_lifecycle_filters_nearby_save_skills(client, make_user, db):
    owner, company, job = setup_job(client, make_user)
    viewer = make_user()
    assert job["skills"] == ["Python", "Design"] and job["applicantCount"] == 0
    assert job["location"]["name"] == "HQ" and job["company"]["id"] == company["id"]
    assert client.get(BASE + "/jobs", params={"query": "python"}).json()["data"][0]["id"] == job["id"]
    assert client.get(BASE + "/jobs", params={"city": "koforidua", "employmentType": "Full-time",
                                             "experienceLevel": "Mid", "companyId": company["id"]}).json()["data"]
    assert client.get(BASE + "/jobs", params={"workArrangement": "Remote"}).json()["data"] == []
    assert client.get(BASE + "/jobs/nearby", params={"lat": 6.09, "lng": -0.26}).json()["data"][0]["distance"] == 0
    assert client.get(BASE + "/jobs/nearby", params={"lat": 6.09, "lng": -0.26,
                                                   "employmentType": "Internship"}).json()["data"] == []
    path = BASE + "/jobs/" + job["id"]
    assert client.get(path).json()["data"]["views"] == 1
    assert client.put(path + "/save", headers=viewer.headers).json()["message"] == "Job saved."
    assert client.put(path + "/save", headers=viewer.headers).json()["message"] == "Already saved."
    assert client.get(BASE + "/jobs/saved", headers=viewer.headers).json()["data"][0]["saved"]
    assert client.get(path, headers=viewer.headers).json()["data"]["saved"]
    assert client.delete(path + "/save", headers=viewer.headers).json()["data"] == {"saved": False}
    assert client.get(BASE + "/jobs/saved", headers=viewer.headers).json()["data"] == []
    assert client.patch(path, headers=viewer.headers, json={"title": "Stolen"}).status_code == 403
    result = client.patch(path, headers=owner.headers, json={"title": "Senior Engineer", "skills": "SQL",
                                                           "deadline": tomorrow(), "salaryMin": 1000})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["skills"] == ["SQL"] and result.json()["data"]["salaryMin"] == 1000
    assert list(db.scalars(select(JobSkill.skill_name).where(JobSkill.job_id == job["id"]))) == ["SQL"]
    assert client.patch(path, headers=owner.headers, json={"status": "invalid"}).json()["detail"] == "Invalid job status."
    assert service.open_job_counts(db, [company["id"]]) == {company["id"]: 1}
    assert service.search_jobs(db, "Senior", viewer.id)[0]["id"] == job["id"]
    assert service.list_jobs_admin(db)[0]["JobID"] == job["id"]
    assert client.patch(path, headers=owner.headers, json={"status": "Closed"}).status_code == 200
    assert client.get(BASE + "/jobs").json()["data"] == []
    assert service.opportunity_stats(db)["jobs"] == 0
    assert service.set_job_status(db, job["id"], "Open")
    assert not service.set_job_status(db, "JOB-missing", "Open")


def test_application_workflow_notifications_signed_cv_and_mail(client, make_user, db, outbox):
    owner, company, job = setup_job(client, make_user)
    applicant, stranger = make_user(), make_user()
    cv = upload(client, applicant, "CVs", PDF, "application/pdf", "resume.pdf")
    path = BASE + "/jobs/" + job["id"]
    response = client.post(path + "/applications", headers=applicant.headers,
                           json={"coverLetter": "Hello", "cvFileId": cv["fileId"], "cvUrl": "https://untrusted"})
    assert response.status_code == 201, response.text
    application_id = response.json()["data"]["applicationId"]
    assert outbox[-1]["to"] == owner.email
    assert client.post(path + "/applications", headers=applicant.headers, json={}).status_code == 409
    assert client.get(path, headers=applicant.headers).json()["data"]["applicationStatus"] == "Applied"
    assert client.get(path + "/applications", headers=stranger.headers).status_code == 403
    applicants = client.get(path + "/applications", headers=owner.headers).json()["data"]
    assert applicants[0]["cvFileId"] == cv["fileId"] and "?token=" in applicants[0]["cvUrl"]
    assert applicants[0]["applicant"]["email"] == applicant.email
    assert client.get(applicants[0]["cvUrl"]).status_code == 200
    applications = client.get(BASE + "/applications/mine", headers=applicant.headers).json()["data"]
    assert applications[0]["id"] == application_id and applications[0]["company"]["name"] == "Acme"
    app_path = BASE + "/applications/" + application_id
    assert client.patch(app_path, headers=stranger.headers, json={"status": "Hired"}).status_code == 403
    assert client.patch(app_path, headers=owner.headers, json={"status": "invalid"}).status_code == 400
    assert client.patch(app_path, headers=owner.headers, json={"status": "Shortlisted"}).json()["message"] == "Application status updated."
    assert client.post(app_path + "/withdraw", headers=stranger.headers).status_code == 403
    assert client.post(app_path + "/withdraw", headers=applicant.headers).status_code == 200
    assert client.get(BASE + "/applications/mine", headers=applicant.headers).json()["data"][0]["stage"] == "Withdrawn"
    assert client.patch(app_path, headers=owner.headers, json={"status": "Hired"}).status_code == 200
    assert client.post(app_path + "/withdraw", headers=applicant.headers).json()["detail"] == "This application can no longer be withdrawn."
    assert service.list_applications_admin(db)[0]["ApplicationID"] == application_id
    employer_notifications = client.get("/api/v1/notifications", headers=owner.headers).json()["data"]["notifications"]
    assert any(n["type"] == "job_application" for n in employer_notifications)
    applicant_notifications = client.get("/api/v1/notifications", headers=applicant.headers).json()["data"]["notifications"]
    assert any(n["type"] == "application_status" for n in applicant_notifications)


def test_application_ownership_deadline_and_best_effort_email(client, make_user, db, outbox, monkeypatch):
    owner, company, job = setup_job(client, make_user)
    applicant, other = make_user(), make_user()
    path = BASE + "/jobs/" + job["id"] + "/applications"
    cv = upload(client, other, "CVs", PDF, "application/pdf", "resume.pdf")
    assert client.post(path, headers=applicant.headers, json={"cvFileId": cv["fileId"]}).json()["code"] == "INVALID_FILE"
    wrong_folder = upload(client, applicant, "Post Media")
    assert client.post(path, headers=applicant.headers, json={"cvFileId": wrong_folder["fileId"]}).status_code == 400
    record = db.get(Job, job["id"])
    record.deadline = utcnow().date() - timedelta(days=1)
    db.commit()
    assert client.post(path, headers=applicant.headers, json={}).json()["code"] == "DEADLINE_PASSED"
    record.deadline = None
    record.status = "Closed"
    db.commit()
    assert client.post(path, headers=applicant.headers, json={}).json()["code"] == "CLOSED"
    record.status = "Open"
    db.commit()
    def unavailable(*args):
        raise email.EmailError("SMTP unavailable")
    monkeypatch.setattr(email, "send_new_application", unavailable)
    assert client.post(path, headers=applicant.headers, json={}).status_code == 201
    set_setting(db, "emailNotifications", "FALSE")
    assert client.post(path, headers=other.headers, json={}).status_code == 201
    assert outbox == []


def test_alerts_validation_and_cross_company_locations(client, make_user, db):
    owner, company, job = setup_job(client, make_user)
    other_owner, other_company, other_job = setup_job(client, make_user)
    response = client.post(BASE + "/jobs", headers=owner.headers, json={
        "companyId": company["id"], "title": "Wrong office", "locationId": other_job["location"]["id"]})
    assert response.status_code == 400 and response.json()["detail"] == "Invalid workplace."
    assert client.post(BASE + "/jobs", headers=owner.headers, json={}).json()["detail"] == "Job title is required."
    assert client.post(BASE + "/jobs", headers=owner.headers, json={"title": "X"}).json()["detail"] == "Please select a company."
    assert client.post(BASE + "/jobs", headers=other_owner.headers,
                        json={"title": "X", "companyId": company["id"]}).status_code == 403
    past = (utcnow().date() - timedelta(days=1)).isoformat()
    assert client.post(BASE + "/jobs", headers=owner.headers, json={
        "title": "X", "companyId": company["id"], "deadline": past}).json()["detail"] == "Deadline must be in the future."
    assert client.post(BASE + "/job-alerts", headers=owner.headers,
                        json={"keywords": "Python", "minSalary": "", "frequency": ""}).status_code == 201
    alert = db.scalar(select(JobAlert).where(JobAlert.user_id == owner.id))
    assert alert.keywords == "Python" and alert.min_salary is None and alert.frequency == "Daily"


def test_events_lifecycle_attendance_capacity_and_cancellation(client, make_user, db):
    organizer, attendee, other = make_user(), make_user(), make_user()
    image = upload(client, organizer, "Event Images")
    response = client.post(BASE + "/events", headers=organizer.headers, json={
        "title": "Career Fair", "eventDate": tomorrow(), "city": "Koforidua",
        "latitude": 6.09, "longitude": -0.26, "coverImage": image["fileId"],
        "registrationRequired": True, "maxAttendees": 1})
    assert response.status_code == 201, response.text
    event = response.json()["data"]
    assert event["organizer"]["userId"] == organizer.id and event["coverImage"] == image["url"]
    assert client.get(BASE + "/events", params={"query": "career", "city": "koforidua", "upcoming": True}).json()["data"][0]["id"] == event["id"]
    assert client.get(BASE + "/events", params={"query": "missing"}).json()["data"] == []
    path = BASE + "/events/" + event["id"]
    assert client.get(path).json()["data"]["myStatus"] == ""
    assert client.get(path, headers=organizer.headers).json()["data"]["canManage"]
    assert client.patch(path, headers=attendee.headers, json={"title": "No"}).status_code == 403
    assert client.delete(path, headers=attendee.headers).status_code == 403
    assert client.put(path + "/attendance", headers=attendee.headers,
                       json={"status": "Invalid"}).json()["detail"] == "Invalid attendance status."
    assert client.put(path + "/attendance", headers=attendee.headers,
                       json={"status": "Attending"}).json()["message"] == "You are registered."
    assert client.put(path + "/attendance", headers=attendee.headers,
                       json={"status": "Attending"}).json()["message"] == "Response updated."
    assert client.put(path + "/attendance", headers=other.headers,
                       json={"status": "Attending"}).json()["code"] == "EVENT_FULL"
    assert client.get(path, headers=attendee.headers).json()["data"]["myStatus"] == "Attending"
    assert client.get(BASE + "/events/mine", headers=attendee.headers).json()["data"][0]["attendeeCount"] == 1
    assert client.delete(path + "/attendance", headers=attendee.headers).json()["data"] == {"status": "none"}
    assert client.get(BASE + "/events/mine", headers=attendee.headers).json()["data"] == []
    assert client.put(path + "/attendance", headers=other.headers, json={"status": "Maybe"}).status_code == 200
    result = client.patch(path, headers=organizer.headers, json={"latitude": "", "longitude": None, "maxAttendees": -1})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["latitude"] is None and result.json()["data"]["maxAttendees"] == 0
    assert db.get(Event, event["id"]).latitude is None
    assert client.patch(path, headers=organizer.headers, json={"status": "Invalid"}).json()["detail"] == "Invalid event status."
    assert client.patch(path, headers=organizer.headers, json={"status": "Completed"}).status_code == 200
    assert client.put(path + "/attendance", headers=attendee.headers, json={"status": "Attending"}).json()["code"] == "EVENT_ENDED"
    assert client.delete(path, headers=organizer.headers).json()["message"] == "Event cancelled."
    assert client.put(path + "/attendance", headers=attendee.headers, json={"status": "Attending"}).json()["code"] == "EVENT_CANCELLED"
    assert client.get(BASE + "/events").json()["data"] == []
    assert service.list_events_admin(db)[0]["Status"] == "Cancelled"
    assert service.set_event_status(db, event["id"], "Active")
    assert not service.set_event_status(db, "EVT-missing", "Active")


def test_event_validation_company_affiliation_and_media_ownership(client, make_user):
    owner, company, job = setup_job(client, make_user)
    stranger = make_user()
    past = (utcnow().date() - timedelta(days=1)).isoformat()
    for body, detail in [
        ({}, "Event title is required."),
        ({"title": "X"}, "Event date is required."),
        ({"title": "X", "eventDate": "nonsense"}, "Invalid event date."),
        ({"title": "X", "eventDate": past}, "Event date cannot be in the past."),
    ]:
        response = client.post(BASE + "/events", headers=owner.headers, json=body)
        assert response.status_code == 400 and response.json()["detail"] == detail
    image = upload(client, stranger, "Event Images")
    assert client.post(BASE + "/events", headers=owner.headers, json={
        "title": "X", "eventDate": tomorrow(), "coverImage": image["fileId"]}).status_code == 400
    event = client.post(BASE + "/events", headers=owner.headers, json={
        "title": "X", "eventDate": tomorrow(), "companyId": company["id"]}).json()["data"]
    assert event["company"]["id"] == company["id"]
    assert service.company_events  # public interface exported
    other = client.post(BASE + "/events", headers=stranger.headers, json={
        "title": "X", "eventDate": tomorrow(), "companyId": company["id"]}).json()["data"]
    assert other["company"] is None


@pytest.mark.parametrize("path,method,body", [
    ("/jobs/JOB-missing", "get", None),
    ("/jobs/JOB-missing", "patch", {"title": "X"}),
    ("/jobs/JOB-missing/applications", "post", {}),
    ("/jobs/JOB-missing/save", "put", None),
    ("/applications/APP-missing/withdraw", "post", None),
    ("/applications/APP-missing", "patch", {"status": "Applied"}),
    ("/events/EVT-missing", "get", None),
    ("/events/EVT-missing", "patch", {"title": "X"}),
    ("/events/EVT-missing", "delete", None),
    ("/events/EVT-missing/attendance", "put", {"status": "Attending"}),
])
def test_not_found(client, make_user, path, method, body):
    kwargs = {"headers": make_user().headers}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(BASE + path, **kwargs)
    assert response.status_code == 404, response.text
