"""User-facing onboarding API (internal v1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.schemas.onboarding_api import (
    EvaluateRoutingBody,
    OnboardingAgentMessage,
    OnboardingBatchUpdate,
    VerifyCompanyBody,
)
from app.services import onboarding_service as onb
from app.services.compliance_deadline_sync import maybe_sync_compliance_deadlines

router = APIRouter(tags=["onboarding"])


@router.get("/v1/onboarding/{user_id}/state")
def onboarding_state(
    user_id: str,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    profile = onb.ensure_profile(db, user_id)
    fields = {f.field_name: f for f in onb.list_profile_fields(db, profile.id)}
    link = profile.company_link
    pipelines = [
        {
            "pipeline_name": r.pipeline_name,
            "enabled": r.enabled,
            "status": r.status,
            "activation_source": r.activation_source,
            "reason_text": r.reason_text,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in sorted(profile.pipeline_rows, key=lambda x: x.pipeline_name)
    ]
    return {
        "profile": {
            "id": profile.id,
            "user_id": profile.user_id,
            "status": profile.status,
            "acting_as": profile.acting_as,
            "business_type": profile.business_type,
            "onboarding_stage": profile.onboarding_stage,
            "completion_percent": profile.completion_percent,
            "summary_json": profile.summary_json,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        },
        "fields": [
            {
                "field_name": f.field_name,
                "value_text": f.field_value_text,
                "value_json": f.field_value_json,
                "source_type": f.source_type,
                "verification_status": f.verification_status,
            }
            for f in sorted(fields.values(), key=lambda x: x.field_name)
        ],
        "company_link": (
            {
                "company_name_input": link.company_name_input,
                "company_number_input": link.company_number_input,
                "matched_company_name": link.matched_company_name,
                "matched_company_number": link.matched_company_number,
                "company_match_status": link.company_match_status,
                "companies_house_verified": link.companies_house_verified,
            }
            if link
            else None
        ),
        "pipelines": pipelines,
        "review_flags": [
            {
                "id": rf.id,
                "flag_type": rf.flag_type,
                "severity": rf.severity,
                "message": rf.message,
                "field_name": rf.field_name,
                "pipeline_name": rf.pipeline_name,
                "resolved": rf.resolved,
                "created_at": rf.created_at.isoformat() if rf.created_at else None,
            }
            for rf in sorted(profile.review_flags, key=lambda x: x.created_at, reverse=True)
        ],
    }


@router.put("/v1/onboarding/{user_id}/fields")
def onboarding_put_fields(
    user_id: str,
    body: OnboardingBatchUpdate,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    profile = onb.ensure_profile(db, user_id)
    for f in body.fields:
        onb.upsert_field(
            db,
            profile,
            field_name=f.field_name,
            value_text=f.value_text,
            value_json=f.value_json,
            source_type=f.source_type,
            verification_status=f.verification_status,
            actor="user_api",
        )
    db.refresh(profile)
    return {"ok": True, "completion_percent": profile.completion_percent}


@router.post("/v1/onboarding/{user_id}/verify-company")
def onboarding_verify_company(
    user_id: str,
    body: VerifyCompanyBody,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    profile = onb.ensure_profile(db, user_id)
    return onb.verify_company(db, settings, profile, name_or_number=body.query, actor="user_api")


def _apply_optional_field_sync(
    db: Session,
    profile,
    body: EvaluateRoutingBody,
) -> None:
    for f in body.fields:
        onb.upsert_field(
            db,
            profile,
            field_name=f.field_name,
            value_text=f.value_text,
            value_json=f.value_json,
            source_type=f.source_type,
            verification_status=f.verification_status,
            actor="user_api",
        )


@router.post("/v1/onboarding/{user_id}/evaluate-routing")
async def onboarding_evaluate(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    profile = onb.ensure_profile(db, user_id)
    raw = await request.body()
    if raw and raw.strip():
        body = EvaluateRoutingBody.model_validate_json(raw)
        _apply_optional_field_sync(db, profile, body)
    onb.evaluate_and_save_pipelines(db, profile, actor="user_api")
    onb.regenerate_review_flags(db, profile)
    db.refresh(profile)
    maybe_sync_compliance_deadlines(db, profile, get_settings())
    db.commit()
    db.refresh(profile)
    return {
        "ok": True,
        "pipelines": [
            {
                "pipeline_name": r.pipeline_name,
                "enabled": r.enabled,
                "status": r.status,
                "activation_source": r.activation_source,
                "reason_text": r.reason_text,
            }
            for r in sorted(profile.pipeline_rows, key=lambda x: x.pipeline_name)
        ],
    }


@router.post("/v1/onboarding/{user_id}/submit")
async def onboarding_submit(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    profile = onb.ensure_profile(db, user_id)
    raw = await request.body()
    if raw and raw.strip():
        body = EvaluateRoutingBody.model_validate_json(raw)
        _apply_optional_field_sync(db, profile, body)
    profile = onb.submit_profile(db, profile, actor="user_api")
    return {"ok": True, "status": profile.status, "summary": profile.summary_json}
