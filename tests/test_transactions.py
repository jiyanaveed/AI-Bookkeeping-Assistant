"""Transactions API + reference uniqueness + mocked receipt vision."""

from __future__ import annotations

import base64
import uuid
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.db_models import User
from app.services import receipt_extraction
from app.services import transaction_service as tx_svc

client = TestClient(app)


def _register_user() -> str:
    email = f"txtest-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post("/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


def test_transactions_list_and_create() -> None:
    uid = _register_user()
    r = client.get("/v1/transactions", params={"user_id": uid})
    assert r.status_code == 200
    assert r.json() == []

    r2 = client.post(
        "/v1/transactions",
        json={
            "user_id": uid,
            "amount": 42.5,
            "currency": "GBP",
            "description": "Test line",
            "source": "api",
        },
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["amount"] == 42.5
    assert body["reference_code"]

    r3 = client.get("/v1/transactions", params={"user_id": uid})
    assert r3.status_code == 200
    assert len(r3.json()) == 1


def test_duplicate_reference_code_rejected() -> None:
    uid = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(User(id=uid, email=f"{uid[:8]}@example.com", password_hash="x"))
        db.commit()
        tx_svc.create_transaction_record(
            db,
            user_id=uid,
            amount=1.0,
            currency="GBP",
            reference_code="DUPE-REF",
        )
        with pytest.raises(IntegrityError):
            tx_svc.create_transaction_record(
                db,
                user_id=uid,
                amount=2.0,
                currency="GBP",
                reference_code="DUPE-REF",
            )
        db.rollback()
    finally:
        db.close()


def test_receipt_extraction_uses_mock_client() -> None:
    uid = _register_user()
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    up = client.post(
        "/v1/uploads",
        data={"user_id": uid},
        files=[("files", ("tiny.png", BytesIO(png), "image/png"))],
    )
    assert up.status_code == 200, up.text
    fid = up.json()["uploads"][0]["id"]

    fake_resp = MagicMock()
    fake_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"merchant":"Test Mart","receipt_date":"2024-06-01","total_amount":9.99,'
                '"tax_amount":null,"currency":"GBP","confidence":0.95}'
            )
        )
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp

    settings = get_settings()
    db = SessionLocal()
    try:
        out = receipt_extraction.extract_receipt_from_upload(
            db,
            settings,
            user_id=uid,
            upload_id=fid,
            client=mock_client,
        )
        assert out["ok"] is True
        assert out["merchant"] == "Test Mart"
        assert abs(float(out["total_amount"]) - 9.99) < 0.001
        assert out["receipt_id"]
        mock_client.chat.completions.create.assert_called_once()
    finally:
        db.close()


def test_chat_fast_path_deterministic_spend() -> None:
    """Spending intent + clear amount/currency + no attachments skips LLM orchestration."""
    uid = _register_user()
    r = client.post(
        "/v1/chat",
        json={
            "message": "Office supplies £18.00",
            "user_id": uid,
            "conversation_id": None,
            "attachment_ids": [],
            "message_intent": "spending",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "Recorded spend" in data["reply"]
    assert "SPEND-" in data["reply"]

    r2 = client.get("/v1/transactions", params={"user_id": uid})
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["source"] == "chat_fast"
    assert abs(float(rows[0]["amount"]) - 18.0) < 0.001
