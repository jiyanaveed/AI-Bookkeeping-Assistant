"""Bearer session lookup and optional user-id alignment checks."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.db_models import AuthSession, User


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def optional_user_from_bearer(db: Session, authorization: str | None) -> User | None:
    raw = _parse_bearer(authorization)
    if not raw:
        return None
    now = datetime.now(timezone.utc)
    sess = (
        db.query(AuthSession)
        .filter(AuthSession.token == raw, AuthSession.expires_at > now)
        .one_or_none()
    )
    if sess is None:
        return None
    return db.get(User, sess.user_id)


def require_user_from_bearer(db: Session, authorization: str | None) -> User:
    user = optional_user_from_bearer(db, authorization)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return user


def bearer_user_if_present(db: Session, authorization: str | None) -> User | None:
    """No header → legacy (unauthenticated) API access. `Bearer …` → must be a valid session."""
    if not authorization or not authorization.strip():
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return require_user_from_bearer(db, authorization)


def assert_path_user_matches(user_id: str, db: Session, authorization: str | None) -> None:
    u = bearer_user_if_present(db, authorization)
    if u is not None and u.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not match user_id on this request.",
        )


def session_for_user(db: Session, user_id: str, *, days: int = 30) -> AuthSession:
    token = secrets.token_urlsafe(32)
    exp = datetime.now(timezone.utc) + timedelta(days=days)
    sess = AuthSession(user_id=user_id, token=token, expires_at=exp)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def revoke_session(db: Session, authorization: str | None) -> int:
    raw = _parse_bearer(authorization)
    if not raw:
        return 0
    n = db.query(AuthSession).filter(AuthSession.token == raw).delete()
    db.commit()
    return n
