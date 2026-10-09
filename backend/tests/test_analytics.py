"""Manager-only analytics composes jobs, applications, and post engagement."""
from app.core.utils import utcnow


def test_analytics_counts_and_permissions(client, make_user):
    owner, applicant, stranger = make_user(), make_user(), make_user()
    company = client.post("/api/v1/companies", headers=owner.headers, json={"name": "Acme"}).json()["data"]
    job = client.post("/api/v1/opportunities/jobs", headers=owner.headers, json={
        "companyId": company["id"], "title": "Engineer"}).json()["data"]
    job_path = "/api/v1/opportunities/jobs/" + job["id"]
    client.get(job_path)
    client.put(job_path + "/save", headers=applicant.headers)
    client.post(job_path + "/applications", headers=applicant.headers, json={})
    post = client.post("/api/v1/feed/posts", headers=owner.headers, json={
        "content": "We are hiring", "companyId": company["id"]})
    assert post.status_code == 201, post.text
    post_id = post.json()["data"]["id"]
    client.post("/api/v1/feed/posts/" + post_id + "/reactions", headers=applicant.headers, json={"type": "like"})
    client.post("/api/v1/feed/posts/" + post_id + "/comments", headers=applicant.headers, json={"content": "Great"})
    path = "/api/v1/analytics/companies/" + company["id"]
    response = client.get(path, headers=owner.headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["jobs"] == 1 and data["jobViews"] == 1 and data["applications"] == 1
    assert data["followers"] == 1 and data["posts"] == 1 and data["engagement"] == 2
    assert data["postEngagement"] == [{"title": "We are hiring", "likes": 1, "comments": 1}]
    assert len(data["applicationTrend"]) == 7 and data["applicationTrend"][-1]["value"] == 1
    assert data["applicationTrend"][-1]["label"] == utcnow().strftime("%m-%d")
    assert data["pipeline"][0] == {"label": "Applied", "value": 1}
    assert client.get(path, headers=stranger.headers).status_code == 403
    assert client.get(path).status_code == 401
    job_analytics = "/api/v1/analytics/jobs/" + job["id"]
    assert client.get(job_analytics, headers=owner.headers).json()["data"] == {
        "views": 1, "applications": 1, "saves": 1}
    assert client.get(job_analytics, headers=stranger.headers).status_code == 403
    assert client.get("/api/v1/analytics/companies/CMP-missing", headers=owner.headers).status_code == 404
    assert client.get("/api/v1/analytics/jobs/JOB-missing", headers=owner.headers).status_code == 404
