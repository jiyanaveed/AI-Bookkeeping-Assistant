"""Admin API gating — replace with RBAC when auth is ready."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config.settings import get_settings


def require_admin(x_admin_key: str | None = Header(None)) -> None:
    settings = get_settings()
    if not settings.admin_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured on the server.",
        )
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access denied.")
