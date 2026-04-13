"""Smoke tests for internal REST endpoints (no OpenAI)."""

import uuid
from datetime import date, timedelta
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_compliance_board_empty() -> None:
    uid = str(uuid.uuid4())
    r = client.get("/v1/reminders/compliance-board", params={"user_id": uid})
    assert r.status_code == 200
    j = r.json()
    assert j["deadlines"] == []
    assert j["manual_reminder_count"] == 0
    assert j["auto_reminder_count"] == 0
    assert j.get("note")


def test_list_reminders_empty() -> None:
    uid = str(uuid.uuid4())
    r = client.get("/v1/reminders", params={"user_id": uid})
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_cancel_reminder() -> None:
    uid = str(uuid.uuid4())
    d = (date.today() + timedelta(days=7)).isoformat()
    r = client.post(
        "/v1/reminders",
        json={
            "user_id": uid,
            "title": "Test title",
            "reminder_type": "accounts",
            "reminder_date": d,
            "channel": "in_app",
        },
    )
    assert r.status_code == 200
    rid = r.json()["id"]
    assert r.json()["title"] == "Test title"

    r2 = client.get("/v1/reminders", params={"user_id": uid})
    assert len(r2.json()) == 1

    r3 = client.post(f"/v1/reminders/{rid}/cancel", params={"user_id": uid})
    assert r3.status_code == 200
    assert r3.json()["status"] == "cancelled"


def test_upload_and_conversation_messages() -> None:
    data = {"user_id": USER}
    up = client.post(
        "/v1/uploads",
        data=data,
        files=[("files", ("note.txt", BytesIO(b"hello"), "text/plain"))],
    )
    assert up.status_code == 200
    fid = up.json()["uploads"][0]["id"]

    # Avoid calling OpenAI: only exercise history + link would be via /v1/chat; check download
    dl = client.get(f"/v1/files/{fid}/content", params={"user_id": USER})
    assert dl.status_code == 200
    assert dl.content == b"hello"
