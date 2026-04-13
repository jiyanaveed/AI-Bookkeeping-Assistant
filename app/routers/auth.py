"""v1 demo auth: email + password + server-side sessions. Replace with IdP/JWT for production."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth_session import require_user_from_bearer, revoke_session, session_for_user
from app.models.db_models import User
from app.schemas.auth_api import (
    LoginRequest,
    MeResponse,
    OnboardingGateInfo,
    RegisterRequest,
    TokenResponse,
    WorkspaceContext,
)
from app.services import onboarding_service as onb
from app.services.passwords import hash_password, verify_password

router = APIRouter(tags=["auth"])

APP_ACCESS_STATUSES = frozenset({"complete", "complete_with_review_flags"})


def _user_by_email(db: Session, email: str) -> User | None:
    e = email.strip().lower()
    return db.query(User).filter(User.email == e).one_or_none()


def _gate(profile) -> OnboardingGateInfo:
    st = profile.status
    return OnboardingGateInfo(
        status=st,
        completion_percent=int(profile.completion_percent or 0),
        can_access_app=st in APP_ACCESS_STATUSES,
        onboarding_stage=profile.onboarding_stage,
    )


@router.post("/v1/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if _user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    u = User(
        email=str(payload.email).strip().lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    sess = session_for_user(db, u.id)
    return TokenResponse(access_token=sess.token, user_id=u.id, email=u.email)


@router.post("/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    u = _user_by_email(db, str(payload.email))
    if u is None or not u.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    sess = session_for_user(db, u.id)
    return TokenResponse(access_token=sess.token, user_id=u.id, email=u.email)


@router.post("/v1/auth/logout")
def logout(
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> dict[str, bool]:
    revoke_session(db, authorization)
    return {"ok": True}


@router.get("/v1/auth/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> MeResponse:
    user = require_user_from_bearer(db, authorization)
    profile = onb.ensure_profile(db, user.id)
    ws = WorkspaceContext(**onb.build_workspace_context(db, profile))
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        onboarding=_gate(profile),
        workspace=ws,
    )
