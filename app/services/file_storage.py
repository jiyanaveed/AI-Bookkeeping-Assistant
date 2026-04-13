"""Store uploaded bytes on local disk — swap for S3/blob later without changing routers."""

from __future__ import annotations

import re
from pathlib import Path

from app.config.settings import Settings

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(name: str, max_len: int = 120) -> str:
    base = name.rsplit("/", 1)[-1].strip() or "file"
    cleaned = _SAFE_NAME.sub("_", base)[:max_len]
    return cleaned or "file"


def absolute_path(settings: Settings, storage_rel_path: str) -> Path:
    return Path(settings.upload_dir).resolve() / storage_rel_path


def save_bytes(
    settings: Settings,
    *,
    user_id: str,
    upload_id: str,
    original_filename: str,
    body: bytes,
    content_type: str | None,
) -> str:
    """Write file; return storage_rel_path relative to upload_dir."""
    safe = sanitize_filename(original_filename)
    rel = f"{user_id}/{upload_id}_{safe}"
    dest = Path(settings.upload_dir).resolve() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return rel
