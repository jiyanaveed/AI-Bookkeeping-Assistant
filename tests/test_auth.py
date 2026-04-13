"""Demo auth + session gating (v1)."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_me_logout() -> None:
    email = f"authtest-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Auth Test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    token = data["access_token"]
    uid = data["user_id"]

    r2 = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["user_id"] == uid
    assert body["onboarding"]["status"] == "not_started"
    assert body["onboarding"]["can_access_app"] is False
    assert "workspace" in body
    assert body["workspace"]["display_line"]
    assert body["workspace"]["companies_house_verified"] is False

    r3 = client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200

    r4 = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 401


def test_chat_forbidden_when_bearer_user_mismatch() -> None:
    email = f"usera-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post("/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r2 = client.post(
        "/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "hi",
            "user_id": "00000000-0000-0000-0000-000000000099",
            "conversation_id": None,
            "attachment_ids": [],
        },
    )
    assert r2.status_code == 403
