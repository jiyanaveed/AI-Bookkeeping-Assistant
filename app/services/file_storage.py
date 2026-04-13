"""Local disk or Supabase Storage — routers use read_upload_bytes / save_upload_bytes."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config.settings import Settings
from app.models.db_models import Upload

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(name: str, max_len: int = 120) -> str:
    base = name.rsplit("/", 1)[-1].strip() or "file"
    cleaned = _SAFE_NAME.sub("_", base)[:max_len]
    return cleaned or "file"


def _object_path(user_id: str, upload_id: str, original_filename: str) -> str:
    safe = sanitize_filename(original_filename)
    return f"{user_id}/{upload_id}_{safe}"


def absolute_path(settings: Settings, storage_rel_path: str) -> Path:
    return Path(settings.upload_dir).resolve() / storage_rel_path


def _supabase_object_url(settings: Settings, object_path: str) -> str:
    base = settings.supabase_url.rstrip("/")
    bucket = (settings.supabase_storage_bucket or "Uploads").strip()
    # Encode each path segment for URL safety
    enc = "/".join(quote(seg, safe="") for seg in object_path.split("/"))
    b = quote(bucket, safe="")
    return f"{base}/storage/v1/object/{b}/{enc}"


def _supabase_headers(settings: Settings) -> dict[str, str]:
    key = settings.supabase_service_role_key.strip()
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }


def save_bytes(
    settings: Settings,
    *,
    user_id: str,
    upload_id: str,
    original_filename: str,
    body: bytes,
    content_type: str | None,
) -> tuple[str, str]:
    """
    Persist file bytes. Returns (storage_rel_path, storage_provider) where provider is
    'local' or 'supabase'. storage_rel_path is the local relative path or the object key in the bucket.
    """
    rel = _object_path(user_id, upload_id, original_filename)
    if settings.use_supabase_storage():
        url = _supabase_object_url(settings, rel)
        headers = {
            **_supabase_headers(settings),
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, content=body, headers=headers)
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase upload failed: {r.status_code} {r.text[:500]}")
        return rel, "supabase"

    dest = Path(settings.upload_dir).resolve() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return rel, "local"


def read_upload_bytes(settings: Settings, upload: Upload) -> bytes:
    """Load raw bytes for an Upload row (local disk or Supabase)."""
    provider = (upload.storage_provider or "local").strip().lower()
    if provider == "supabase":
        if not settings.use_supabase_storage():
            raise RuntimeError("Upload is in Supabase but credentials are not configured.")
        url = _supabase_object_url(settings, upload.storage_rel_path)
        headers = _supabase_headers(settings)
        with httpx.Client(timeout=120.0) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 404:
                raise FileNotFoundError("Object not found in storage.")
            if r.status_code >= 400:
                raise RuntimeError(f"Supabase download failed: {r.status_code} {r.text[:500]}")
            return r.content

    path = absolute_path(settings, upload.storage_rel_path)
    if not path.is_file():
        raise FileNotFoundError("File missing on disk.")
    return path.read_bytes()
