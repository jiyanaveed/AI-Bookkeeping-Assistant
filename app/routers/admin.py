"""Admin-only onboarding & pipeline monitor API."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config.settings import Settings, get_settings
from app.deps.admin_auth import require_admin
from app.db.session import get_db
from app.models.db_models import (
    OnboardingCompanyLink,
    OnboardingEvent,
    OnboardingProfile,
    OnboardingReviewFlag,
    User,
)
from app.services import onboarding_service as onb

router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


def _handoff_summary(profile: OnboardingProfile) -> dict:
    ps = {p.pipeline_name: p for p in profile.pipeline_rows}
    ch = ps.get("companies_house")
    return {
        "onboarding_agent": {
            "currently_active": profile.status in ("not_started", "in_progress"),
            "reason": "Structured signup until onboarding status completes.",
        },
        "supervisor_agent": {
            "currently_active": True,
            "reason": "Final orchestration for main /v1/chat.",
        },
        "compliance_agent": {
            "currently_active": bool(ch and ch.enabled),
            "reason": "Companies House tools when pipeline active or user requests.",
        },
        "bookkeeping_agent": {
            "currently_active": True,
            "reason": "Bookkeeping specialist + tools for spend and receipt extraction from chat.",
        },
        "intake_agent": {
            "currently_active": False,
            "reason": "Partial; not invoked on every message.",
        },
    }


def _reminder_readiness(db: Session, profile: OnboardingProfile, user: User | None) -> dict:
    fm = onb._field_map(db, profile.id)
    channel = onb.txt_from_fm(fm, "preferred_reminder_channel") or ""
    email = onb.txt_from_fm(fm, "email") or (user.email if user else None)
    phone = onb.txt_from_fm(fm, "phone_number") or (user.phone_number if user else None)
    pr = next((p for p in profile.pipeline_rows if p.pipeline_name == "reminders"), None)
    delivery = "stub_only"
    if pr:
        if pr.status == "active":
            delivery = "ready" if channel in ("in_app", "email", "") or (channel == "email" and email) else "setup_incomplete"
        elif pr.status == "setup_incomplete":
            delivery = "setup_incomplete"
    missing = []
    if channel == "email" and not email:
        missing.append("email")
    if channel == "whatsapp" and not phone:
        missing.append("phone_number")
    return {
        "preferred_reminder_channel": channel or None,
        "email_present": bool(email),
        "phone_present": bool(phone),
        "reminders_pipeline_status": pr.status if pr else None,
        "delivery_readiness": delivery,
        "missing_for_channel": missing,
    }


@router.get("/v1/admin/users/search")
def admin_search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = q.strip()
    seen: set[str] = set()
    out: list[dict] = []

    u = db.get(User, q)
    if u:
        seen.add(u.id)
        out.append({"user_id": u.id, "email": u.email, "match": "user_id"})

    for u in db.query(User).filter(User.email.isnot(None), User.email.ilike(f"%{q}%")).limit(25):
        if u.id not in seen:
            seen.add(u.id)
            out.append({"user_id": u.id, "email": u.email, "match": "email"})

    for link in (
        db.query(OnboardingCompanyLink)
        .filter(
            or_(
                OnboardingCompanyLink.matched_company_number.ilike(f"%{q}%"),
                OnboardingCompanyLink.company_name_input.ilike(f"%{q}%"),
            )
        )
        .limit(25)
    ):
        prof = db.get(OnboardingProfile, link.onboarding_profile_id)
        if prof and prof.user_id not in seen:
            seen.add(prof.user_id)
            u = db.get(User, prof.user_id)
            out.append(
                {
                    "user_id": prof.user_id,
                    "email": u.email if u else None,
                    "match": "company",
                    "company_number": link.matched_company_number,
                }
            )
    return out


@router.get("/v1/admin/users/{user_id}/monitor")
def admin_monitor(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    profile = (
        db.query(OnboardingProfile)
        .options(
            joinedload(OnboardingProfile.fields),
            joinedload(OnboardingProfile.company_link),
            joinedload(OnboardingProfile.review_flags),
            joinedload(OnboardingProfile.pipeline_rows),
        )
        .filter(OnboardingProfile.user_id == user_id)
        .one_or_none()
    )
    if not profile:
        return {"exists": False, "user_id": user_id}
    user = db.get(User, user_id)
    fields = onb.list_profile_fields(db, profile.id)
    fm = {f.field_name: f for f in fields}
    events = (
        db.query(OnboardingEvent)
        .filter(OnboardingEvent.onboarding_profile_id == profile.id)
        .order_by(OnboardingEvent.created_at.desc())
        .limit(100)
        .all()
    )
    link = profile.company_link
    return {
        "exists": True,
        "user_id": user_id,
        "user": {
            "email": user.email if user else None,
            "phone_number": user.phone_number if user else None,
            "preferred_channel": user.preferred_channel if user else None,
        },
        "profile_overview": {
            "status": profile.status,
            "acting_as": profile.acting_as,
            "business_type": profile.business_type,
            "onboarding_stage": profile.onboarding_stage,
            "completion_percent": profile.completion_percent,
            "preferred_reminder_channel": onb.txt_from_fm(fm, "preferred_reminder_channel"),
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        },
        "company_verification": (
            {
                "company_name_input": link.company_name_input,
                "company_number_input": link.company_number_input,
                "matched_company_name": link.matched_company_name,
                "matched_company_number": link.matched_company_number,
                "company_match_status": link.company_match_status,
                "companies_house_verified": link.companies_house_verified,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
                "profile_snapshot": link.profile_snapshot_json,
            }
            if link
            else None
        ),
        "field_matrix": [
            {
                "field_name": f.field_name,
                "value_text": f.field_value_text,
                "value_json": f.field_value_json,
                "source_type": f.source_type,
                "verification_status": f.verification_status,
                "is_required": f.is_required,
                "confidence": float(f.confidence) if f.confidence is not None else None,
                "last_updated_by": f.last_updated_by,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            }
            for f in fields
        ],
        "review_flags": [
            {
                "id": rf.id,
                "severity": rf.severity,
                "flag_type": rf.flag_type,
                "message": rf.message,
                "field_name": rf.field_name,
                "pipeline_name": rf.pipeline_name,
                "resolved": rf.resolved,
                "resolved_by": rf.resolved_by,
                "resolved_at": rf.resolved_at.isoformat() if rf.resolved_at else None,
                "created_at": rf.created_at.isoformat() if rf.created_at else None,
            }
            for rf in sorted(profile.review_flags, key=lambda x: x.created_at, reverse=True)
        ],
        "pipeline_board": [
            {
                "pipeline_name": p.pipeline_name,
                "enabled": p.enabled,
                "status": p.status,
                "activation_source": p.activation_source,
                "reason_text": p.reason_text,
                "metadata_json": p.metadata_json,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in sorted(profile.pipeline_rows, key=lambda x: x.pipeline_name)
        ],
        "agent_handoff": _handoff_summary(profile),
        "event_timeline": [
            {
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "event_type": e.event_type,
                "actor_type": e.actor_type,
                "actor_name": e.actor_name,
                "payload": e.event_payload_json,
            }
            for e in events
        ],
        "reminder_readiness": _reminder_readiness(db, profile, user),
        "summary_json": profile.summary_json,
    }


@router.post("/v1/admin/users/{user_id}/rerun-routing")
def admin_rerun_routing(user_id: str, db: Session = Depends(get_db)) -> dict:
    profile = onb.ensure_profile(db, user_id)
    onb.evaluate_and_save_pipelines(db, profile, actor="admin")
    onb.regenerate_review_flags(db, profile)
    onb.log_event(db, profile, "routing_evaluated", "admin", "admin_api", {"action": "rerun"})
    db.commit()
    return {"ok": True}


@router.post("/v1/admin/users/{user_id}/refresh-company-verification")
def admin_refresh_company(
    user_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    q: str = Query(..., min_length=1),
) -> dict:
    profile = onb.ensure_profile(db, user_id)
    return onb.verify_company(db, settings, profile, name_or_number=q, actor="admin")


@router.patch("/v1/admin/review-flags/{flag_id}/resolve")
def admin_resolve_flag(
    flag_id: str,
    resolved_by: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    rf = db.get(OnboardingReviewFlag, flag_id)
    if not rf:
        return {"ok": False, "error": "not found"}
    pid = rf.onboarding_profile_id
    rf.resolved = True
    rf.resolved_by = resolved_by
    rf.resolved_at = datetime.now(timezone.utc)
    db.commit()
    prof = db.get(OnboardingProfile, pid)
    if prof:
        onb.log_event(
            db,
            prof,
            "admin_override",
            "admin",
            resolved_by,
            {"action": "resolve_flag", "flag_id": flag_id},
        )
        db.commit()
    return {"ok": True}
