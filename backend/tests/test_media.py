from tests.conftest import MP4, PDF, PNG, upload


def test_upload_and_serve_public_image(client, make_user):
    user = make_user()
    data = upload(client, user, "Post Media")
    assert data["fileId"].startswith("MED-") and data["url"] == f"/api/v1/media/{data['fileId']}"
    served = client.get(data["url"])  # no auth needed: <img> tags send no token
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"


def test_video_supports_range_requests(client, make_user):
    user = make_user()
    data = upload(client, user, "Stories", content=MP4, mime="video/mp4", name="clip.mp4")
    partial = client.get(data["url"], headers={"Range": "bytes=0-9"})
    assert partial.status_code == 206 and partial.content == MP4[:10]


def test_rejects_bad_type_spoofed_content_and_oversize(client, make_user, monkeypatch):
    user = make_user()
    files = lambda content, mime: {"file": ("f", content, mime)}  # noqa: E731
    wrong_type = client.post("/api/v1/media", headers=user.headers, data={"folder": "Post Media"},
                             files=files(b"<script>alert(1)</script>", "text/html"))
    assert wrong_type.status_code == 415
    spoofed = client.post("/api/v1/media", headers=user.headers, data={"folder": "Post Media"},
                          files=files(b"<html><script>x</script>", "image/png"))
    assert spoofed.status_code == 415 and spoofed.json()["code"] == "INVALID_FILE_TYPE"
    bad_folder = client.post("/api/v1/media", headers=user.headers, data={"folder": "Secrets"}, files=files(PNG, "image/png"))
    assert bad_folder.json()["detail"] == "Invalid upload folder."
    from app.core.config import settings
    monkeypatch.setattr(settings, "max_upload_bytes", 32)
    big = client.post("/api/v1/media", headers=user.headers, data={"folder": "Post Media"}, files=files(PNG, "image/png"))
    assert big.status_code == 413 and big.json()["detail"] == "File is too large. Maximum size is 0 MB."


def test_private_cv_needs_owner_staff_or_signed_link(client, make_user):
    owner, stranger, admin = make_user(), make_user(), make_user(role="Admin")
    data = upload(client, owner, "CVs", content=PDF, mime="application/pdf", name="cv.pdf")
    plain = f"/api/v1/media/{data['fileId']}"
    assert client.get(plain).status_code == 403
    assert client.get(plain, headers=stranger.headers).status_code == 403
    assert client.get(plain, headers=owner.headers).status_code == 200
    assert client.get(plain, headers=admin.headers).status_code == 200
    signed = client.get(data["url"])  # the upload result carries a signed link
    assert signed.status_code == 200 and "attachment" in signed.headers["content-disposition"]


def test_upload_requires_verified_user(client, make_user):
    user = make_user(verified=False)
    response = client.post("/api/v1/media", headers=user.headers, data={"folder": "Post Media"},
                           files={"file": ("p.png", PNG, "image/png")})
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"
