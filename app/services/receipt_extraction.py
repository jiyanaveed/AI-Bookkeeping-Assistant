"""Multimodal receipt extraction via OpenAI vision (images only in v1)."""

from __future__ import annotations

import base64
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.models.db_models import Receipt, Upload
from app.services.file_storage import absolute_path


def _mime_for_upload(upload: Upload) -> str:
    ct = (upload.content_type or "").lower().strip()
    if "png" in ct:
        return "image/png"
    if "webp" in ct:
        return "image/webp"
    if "jpeg" in ct or "jpg" in ct:
        return "image/jpeg"
    name = (upload.original_filename or "").lower()
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        return "image/jpeg"
    return "image/jpeg"


def _is_probably_pdf(upload: Upload) -> bool:
    ct = (upload.content_type or "").lower()
    return "pdf" in ct or (upload.original_filename or "").lower().endswith(".pdf")


def extract_receipt_from_upload(
    db: Session,
    settings: Settings,
    *,
    user_id: str,
    upload_id: str,
    message_id: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """
    Run vision model on upload bytes; persist Receipt row; return structured result + receipt_id.
    PDFs are not processed in v1 (upload a photo or screenshot instead).
    """
    if not settings.openai_api_key.strip():
        return {"ok": False, "error": "OPENAI_API_KEY not configured."}

    up = db.get(Upload, upload_id)
    if up is None or up.user_id != user_id:
        return {"ok": False, "error": "Upload not found for this user."}

    if _is_probably_pdf(up):
        return {
            "ok": False,
            "error": "PDF receipts are not supported yet—please upload a photo or screenshot (PNG/JPEG).",
        }

    path: Path = absolute_path(settings, up.storage_rel_path)
    if not path.is_file():
        return {"ok": False, "error": "File bytes missing on server."}

    data = path.read_bytes()
    if len(data) > 20_000_000:
        return {"ok": False, "error": "Image too large."}

    mime = _mime_for_upload(up)
    b64 = base64.standard_b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

    model = (settings.receipt_vision_model or "gpt-4o-mini").strip()

    system = (
        "You extract data from UK retail receipt photos. Reply with ONLY a single JSON object, no markdown fence, "
        "keys: merchant (string or null), receipt_date (YYYY-MM-DD or null), total_amount (number or null), "
        "tax_amount (number or null), currency (ISO code like GBP or null), confidence (0 to 1). "
        "If unreadable, use nulls and confidence near 0."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract receipt fields."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            max_tokens=500,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}

    raw = (resp.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "merchant": None,
            "receipt_date": None,
            "total_amount": None,
            "tax_amount": None,
            "currency": None,
            "confidence": 0.0,
            "raw_model_output": raw[:2000],
        }

    conf = parsed.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_f = None

    rd = parsed.get("receipt_date")
    receipt_date: date | None = None
    if rd:
        try:
            receipt_date = date.fromisoformat(str(rd)[:10])
        except ValueError:
            receipt_date = None

    total = parsed.get("total_amount")
    tax = parsed.get("tax_amount")
    try:
        total_f = float(total) if total is not None else None
    except (TypeError, ValueError):
        total_f = None
    try:
        tax_f = float(tax) if tax is not None else None
    except (TypeError, ValueError):
        tax_f = None

    rec = Receipt(
        user_id=user_id,
        upload_id=upload_id,
        message_id=message_id,
        merchant=(str(parsed.get("merchant"))[:512] if parsed.get("merchant") else None),
        receipt_date=receipt_date,
        total_amount=total_f,
        tax_amount=tax_f,
        currency=(str(parsed.get("currency") or "GBP")[:16] if total_f is not None else None),
        extracted_json=parsed if isinstance(parsed, dict) else {"raw": str(parsed)},
        extraction_confidence=conf_f,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "ok": True,
        "receipt_id": rec.id,
        "merchant": rec.merchant,
        "receipt_date": rec.receipt_date.isoformat() if rec.receipt_date else None,
        "total_amount": float(rec.total_amount) if rec.total_amount is not None else None,
        "tax_amount": float(rec.tax_amount) if rec.tax_amount is not None else None,
        "currency": rec.currency,
        "confidence": float(rec.extraction_confidence) if rec.extraction_confidence is not None else None,
    }
