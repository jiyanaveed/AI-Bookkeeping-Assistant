"""Onboarding persistence, verification, routing, flags — backend source of truth."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.models.db_models import (
    OnboardingCompanyLink,
    OnboardingEvent,
    OnboardingField,
    OnboardingProfile,
    OnboardingReviewFlag,
    PipelineStatus,
    User,
)
from app.services.companies_house import CompaniesHouseClient, normalize_profile
from app.services.company_search_match import classify_company_search_results, pick_dominant_strong_matches
from app.services.pipeline_routing import compute_pipeline_decisions

REQUIRED_BY_TYPE: dict[str, list[str]] = {
    "sole_trader": [
        "acting_as",
        "business_type",
        "income_types",
        "self_assessment_registered",
        "preferred_reminder_channel",
        "email",
        "date_started",
    ],
    "limited_company": [
        "acting_as",
        "business_type",
        "company_registration_status",
        "company_name_or_number",
        "company_trade_status",
        "preferred_reminder_channel",
        "email",
    ],
    "landlord": [
        "acting_as",
        "business_type",
        "income_types",
        "self_assessment_registered",
        "preferred_reminder_channel",
        "email",
        "date_started",
    ],
    "sole_trader_and_landlord": [
        "acting_as",
        "business_type",
        "income_types",
        "self_assessment_registered",
        "preferred_reminder_channel",
        "email",
        "date_started",
    ],
    "partnership": [
        "acting_as",
        "business_type",
        "income_types",
        "self_assessment_registered",
        "preferred_reminder_channel",
        "email",
    ],
    "accountant_or_bookkeeper": ["acting_as", "business_type", "email"],
    "not_sure": ["acting_as", "business_type", "email"],
}

# virtual field satisfied if any of these present
DATE_ALIASES = ("business_start_date", "trading_start_date", "property_income_start_date")


def ensure_profile(db: Session, user_id: str) -> OnboardingProfile:
    if db.get(User, user_id) is None:
        db.add(User(id=user_id))
        db.commit()
    p = db.query(OnboardingProfile).filter(OnboardingProfile.user_id == user_id).one_or_none()
    if p:
        return p
    p = OnboardingProfile(user_id=user_id, status="not_started", onboarding_stage="account_type")
    db.add(p)
    db.commit()
    db.refresh(p)
    log_event(db, p, "onboarding_started", "system", "onboarding_service", {})
    db.commit()
    return p


def log_event(
    db: Session,
    profile: OnboardingProfile,
    event_type: str,
    actor_type: str,
    actor_name: str,
    payload: dict[str, Any] | None,
) -> None:
    db.add(
        OnboardingEvent(
            onboarding_profile_id=profile.id,
            event_type=event_type,
            actor_type=actor_type,
            actor_name=actor_name,
            event_payload_json=payload,
        )
    )


def _field_map(db: Session, profile_id: str) -> dict[str, OnboardingField]:
    rows = db.query(OnboardingField).filter(OnboardingField.onboarding_profile_id == profile_id).all()
    return {r.field_name: r for r in rows}


def list_profile_fields(db: Session, profile_id: str) -> list[OnboardingField]:
    return (
        db.query(OnboardingField)
        .filter(OnboardingField.onboarding_profile_id == profile_id)
        .order_by(OnboardingField.field_name)
        .all()
    )


def _has_value(fm: dict[str, OnboardingField], name: str) -> bool:
    row = fm.get(name)
    if not row:
        return False
    if row.field_value_json is not None:
        if isinstance(row.field_value_json, list):
            return len(row.field_value_json) > 0
        return True
    return bool(row.field_value_text and str(row.field_value_text).strip())


def _workspace_display_line(
    *,
    business_type: str | None,
    acting_as: str | None,
    companies_house_verified: bool,
    company_name: str | None,
    company_number: str | None,
) -> str:
    """Single human-readable line for the workspace header (UK onboarding v1, one entity per user)."""
    bt = (business_type or "").strip() or None
    aa = (acting_as or "").strip() or None
    name = (company_name or "").strip() or None
    num = (company_number or "").strip() or None

    prefix = ""
    if aa == "accountant_or_bookkeeper_for_clients":
        prefix = "Practitioner account — "

    if bt == "limited_company":
        if companies_house_verified and (name or num):
            if name and num:
                return f"{prefix}Active company: {name} · {num}"
            if num:
                return f"{prefix}Active company: #{num}"
            return f"{prefix}Active company: {name}"
        return f"{prefix}Limited company — verify and link Companies House in Setup so we use the right entity"

    if bt == "sole_trader":
        return f"{prefix}Sole trader — no limited company on this profile"
    if bt == "sole_trader_and_landlord":
        return f"{prefix}Sole trader & landlord"
    if bt == "landlord":
        return f"{prefix}Landlord (property income)"
    if bt == "partnership":
        return f"{prefix}Partnership"
    if bt == "accountant_or_bookkeeper":
        return f"{prefix}Accountant / bookkeeper profile"
    if bt == "not_sure":
        return f"{prefix}Business type not confirmed — finish Setup"

    if bt:
        readable = bt.replace("_", " ").title()
        return f"{prefix}{readable}"

    return f"{prefix}Complete Setup to add your business profile"


def build_workspace_context(db: Session, profile: OnboardingProfile) -> dict[str, Any]:
    """Fields for /v1/auth/me workspace strip (primary onboarding entity only; not multi-company)."""
    snap = build_routing_snapshot(db, profile)
    link = profile.company_link
    bt = snap.get("business_type") or profile.business_type
    acting = snap.get("acting_as") or profile.acting_as
    if isinstance(bt, str):
        bt = bt.strip() or None
    if isinstance(acting, str):
        acting = acting.strip() or None

    verified = bool(link and link.companies_house_verified)
    name = (link.matched_company_name if link else None) or None
    num = (link.matched_company_number if link else None) or None
    if name:
        name = name.strip() or None
    if num:
        num = num.strip() or None

    display = _workspace_display_line(
        business_type=bt,
        acting_as=acting,
        companies_house_verified=verified,
        company_name=name,
        company_number=num,
    )
    return {
        "business_type": bt,
        "acting_as": acting,
        "primary_company_name": name,
        "primary_company_number": num,
        "companies_house_verified": verified,
        "display_line": display,
    }


def build_routing_snapshot(db: Session, profile: OnboardingProfile) -> dict[str, Any]:
    fm = _field_map(db, profile.id)
    snap: dict[str, Any] = {}

    def txt(name: str) -> str | None:
        r = fm.get(name)
        if not r or not r.field_value_text:
            return None
        return r.field_value_text.strip()

    for key in (
        "acting_as",
        "business_type",
        "company_registration_status",
        "company_name_or_number",
        "company_trade_status",
        "self_assessment_registered",
        "utr_available",
        "government_gateway_access",
        "vat_status",
        "vat_number",
        "payroll_status",
        "first_payday_date",
        "paye_reference_available",
        "employee_count",
        "uk_nation",
        "preferred_reminder_channel",
        "email",
        "phone_number",
        "estimated_12_month_taxable_turnover",
        "estimated_annual_self_employment_income",
        "estimated_annual_property_income",
    ):
        v = txt(key)
        if v:
            snap[key] = v

    inc = fm.get("income_types")
    if inc and inc.field_value_json is not None:
        snap["income_types"] = inc.field_value_json
    elif inc and inc.field_value_text:
        snap["income_types"] = [x.strip() for x in inc.field_value_text.split(",") if x.strip()]

    if profile.business_type:
        snap.setdefault("business_type", profile.business_type)
    if profile.acting_as:
        snap.setdefault("acting_as", profile.acting_as)

    link = profile.company_link
    if link:
        snap["company_match_status"] = link.company_match_status
        snap["companies_house_verified"] = link.companies_house_verified
        if link.matched_company_number:
            snap["matched_company_number"] = link.matched_company_number
    return snap


def txt_from_fm(fm: dict[str, OnboardingField], name: str) -> str | None:
    r = fm.get(name)
    if r and r.field_value_text:
        return r.field_value_text.strip()
    return None


def recompute_completion(db: Session, profile: OnboardingProfile) -> None:
    fm = _field_map(db, profile.id)
    bt = profile.business_type or txt_from_fm(fm, "business_type") or "not_sure"
    required = REQUIRED_BY_TYPE.get(bt, REQUIRED_BY_TYPE["not_sure"])
    link = (
        db.query(OnboardingCompanyLink)
        .filter(OnboardingCompanyLink.onboarding_profile_id == profile.id)
        .one_or_none()
    )
    filled = 0
    for name in required:
        if name == "date_started":
            if any(_has_value(fm, d) for d in DATE_ALIASES):
                filled += 1
        elif name == "company_name_or_number" and bt == "limited_company":
            if _has_value(fm, name) or (link and link.matched_company_number):
                filled += 1
        elif _has_value(fm, name):
            filled += 1
    total = len(required)
    profile.completion_percent = int(100 * filled / total) if total else 0
    if profile.status == "not_started" and filled > 0:
        profile.status = "in_progress"
    profile.onboarding_stage = profile.onboarding_stage or "account_type"


def upsert_field(
    db: Session,
    profile: OnboardingProfile,
    *,
    field_name: str,
    value_text: str | None = None,
    value_json: list | dict | None = None,
    source_type: str = "user_provided",
    verification_status: str = "unverified",
    is_required: bool = False,
    actor: str = "user_api",
) -> OnboardingField:
    existed = (
        db.query(OnboardingField)
        .filter(
            OnboardingField.onboarding_profile_id == profile.id,
            OnboardingField.field_name == field_name,
        )
        .one_or_none()
    )
    if existed is None:
        row = OnboardingField(
            onboarding_profile_id=profile.id,
            field_name=field_name,
            source_type=source_type,
            verification_status=verification_status,
            is_required=is_required,
            captured_by_agent=actor if "agent" in actor else None,
            last_updated_by=actor,
        )
        db.add(row)
    else:
        row = existed
    if value_text is not None:
        row.field_value_text = value_text
    if value_json is not None:
        row.field_value_json = value_json
    row.source_type = source_type
    row.verification_status = verification_status
    row.last_updated_by = actor
    row.updated_at = datetime.now(timezone.utc)

    if field_name == "acting_as":
        profile.acting_as = value_text
    if field_name == "business_type":
        profile.business_type = value_text

    if field_name == "email" and value_text:
        u = db.get(User, profile.user_id)
        if u:
            u.email = value_text
    if field_name == "phone_number" and value_text:
        u = db.get(User, profile.user_id)
        if u:
            u.phone_number = value_text
    if field_name == "preferred_reminder_channel" and value_text:
        u = db.get(User, profile.user_id)
        if u:
            u.preferred_channel = value_text

    profile.updated_at = datetime.now(timezone.utc)
    recompute_completion(db, profile)
    log_event(
        db,
        profile,
        "field_updated" if existed else "field_captured",
        "user" if actor == "user_api" else "onboarding_agent",
        actor,
        {"field_name": field_name},
    )
    db.commit()
    db.refresh(row)
    return row


def regenerate_review_flags(db: Session, profile: OnboardingProfile) -> None:
    db.query(OnboardingReviewFlag).filter(
        OnboardingReviewFlag.onboarding_profile_id == profile.id,
        OnboardingReviewFlag.resolved.is_(False),
    ).delete(synchronize_session=False)
    snap = build_routing_snapshot(db, profile)
    fm = _field_map(db, profile.id)

    def add(flag_type: str, severity: str, message: str, field: str | None = None, pipe: str | None = None):
        db.add(
            OnboardingReviewFlag(
                onboarding_profile_id=profile.id,
                flag_type=flag_type,
                severity=severity,
                message=message,
                field_name=field,
                pipeline_name=pipe,
            )
        )

    if txt_from_fm(fm, "self_assessment_registered") == "not_sure":
        add("self_assessment_uncertain", "medium", "Self Assessment registration unclear.", "self_assessment_registered")

    link = profile.company_link
    if link and link.company_match_status == "ambiguous_match":
        add("ambiguous_company_match", "high", "Multiple possible Companies House matches.", None, "companies_house")

    if link and link.company_match_status in ("weak_match", "no_verified_match") and _txt(
        snap.get("company_registration_status")
    ) == "already_registered":
        add("ambiguous_company_match", "high", "Company could not be strongly verified.", None, "companies_house")

    vat_t = _parse_float(txt_from_fm(fm, "estimated_12_month_taxable_turnover"))
    if vat_t and vat_t >= 85_000 and _txt(snap.get("vat_status")) not in ("vat_registered", "not_vat_registered"):
        add("possible_vat_review", "medium", "Turnover suggests VAT threshold review.", "estimated_12_month_taxable_turnover", "vat")

    ch = _txt(snap.get("preferred_reminder_channel"))
    if ch == "email" and not _txt(snap.get("email")):
        add("reminder_setup_incomplete", "medium", "Email channel chosen but no email stored.", "email", "reminders")

    db.commit()


def evaluate_and_save_pipelines(db: Session, profile: OnboardingProfile, actor: str) -> None:
    snap = build_routing_snapshot(db, profile)
    decisions = compute_pipeline_decisions(snap)
    for d in decisions:
        row = (
            db.query(PipelineStatus)
            .filter(
                PipelineStatus.onboarding_profile_id == profile.id,
                PipelineStatus.pipeline_name == d["pipeline_name"],
            )
            .one_or_none()
        )
        if row is None:
            row = PipelineStatus(onboarding_profile_id=profile.id, pipeline_name=d["pipeline_name"])
            db.add(row)
        row.enabled = d["enabled"]
        row.status = d["status"]
        row.activation_source = d["activation_source"]
        row.reason_text = d.get("reason_text")
        row.metadata_json = d.get("metadata_json")
        row.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_event(db, profile, "routing_evaluated", "system", actor, {"pipelines": [x["pipeline_name"] for x in decisions]})


def _parse_float(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _txt(s: Any) -> str:
    return str(s).strip().lower() if s is not None else ""


def _sync_routing_after_company_verification(db: Session, profile: OnboardingProfile, actor: str) -> None:
    """Recompute pipelines and review flags after CH link changes so summary stays aligned."""
    db.refresh(profile)
    evaluate_and_save_pipelines(db, profile, actor=actor)
    regenerate_review_flags(db, profile)
    from app.services.compliance_deadline_sync import maybe_sync_compliance_deadlines

    maybe_sync_compliance_deadlines(db, profile, get_settings())


def verify_company(
    db: Session,
    settings: Settings,
    profile: OnboardingProfile,
    *,
    name_or_number: str,
    actor: str = "user_api",
) -> dict[str, Any]:
    ensure_company_link(db, profile)
    link = profile.company_link
    assert link is not None
    q = name_or_number.strip()
    link.company_name_input = q
    link.company_number_input = None
    if re.match(r"^[A-Z0-9]{6,10}$", q.upper().replace(" ", "")):
        link.company_number_input = q.upper().replace(" ", "")

    _actor_type = "user" if actor == "user_api" else "admin" if actor == "admin" else "onboarding_agent"
    log_event(db, profile, "company_verification_attempted", _actor_type, actor, {"query": name_or_number})
    db.commit()

    client = CompaniesHouseClient(settings.companies_house_api_key)
    if not settings.companies_house_api_key.strip():
        link.company_match_status = "no_verified_match"
        link.companies_house_verified = False
        link.updated_at = datetime.now(timezone.utc)
        db.commit()
        _sync_routing_after_company_verification(db, profile, actor=actor)
        return {"ok": False, "error": "COMPANIES_HOUSE_API_KEY not configured"}

    try:
        if link.company_number_input:
            data = client.get_company_raw(link.company_number_input)
            if data:
                prof = normalize_profile(data)
                link.matched_company_name = prof.get("company_name")
                link.matched_company_number = prof.get("company_number")
                link.company_match_status = "strong_match"
                link.companies_house_verified = True
                link.profile_snapshot_json = prof
                link.updated_at = datetime.now(timezone.utc)
                db.commit()
                log_event(
                    db,
                    profile,
                    "company_verified",
                    "system",
                    actor,
                    {"number": prof.get("company_number")},
                )
                db.commit()
                _sync_routing_after_company_verification(db, profile, actor=actor)
                return {"ok": True, "match_status": "strong_match", "profile": prof}

        items = client.search_companies(q).get("items") or []
        classified = classify_company_search_results(q, items)
        strong_raw = list(classified.get("strong_matches") or [])
        strong_for_selection = pick_dominant_strong_matches(q, strong_raw)
        if strong_for_selection != strong_raw:
            classified = {
                **classified,
                "strong_matches": strong_for_selection,
                "has_strong_match": len(strong_for_selection) > 0,
                "alternate_strong_candidates_ignored": max(0, len(strong_raw) - len(strong_for_selection)),
            }
    except Exception as e:
        link.company_match_status = "no_verified_match"
        link.companies_house_verified = False
        link.updated_at = datetime.now(timezone.utc)
        db.commit()
        _sync_routing_after_company_verification(db, profile, actor=actor)
        return {"ok": False, "error": str(e)}

    strong = list(classified.get("strong_matches") or [])
    if len(strong) == 1:
        num = strong[0]["company_number"]
        data = client.get_company_raw(str(num))
        prof = normalize_profile(data) if data else {}
        link.matched_company_name = strong[0].get("company_name")
        link.matched_company_number = num
        link.company_match_status = "strong_match"
        link.companies_house_verified = bool(data)
        link.profile_snapshot_json = prof
        link.updated_at = datetime.now(timezone.utc)
        db.commit()
        log_event(db, profile, "company_verified", "system", actor, {"number": num})
        db.commit()
        _sync_routing_after_company_verification(db, profile, actor=actor)
        return {"ok": True, "classified": classified, "profile": prof}
    if len(strong) > 1:
        link.company_match_status = "ambiguous_match"
        link.companies_house_verified = False
        link.profile_snapshot_json = classified
        link.updated_at = datetime.now(timezone.utc)
        db.commit()
        _sync_routing_after_company_verification(db, profile, actor=actor)
        return {"ok": True, "classified": classified}
    loose = classified.get("loosely_related_candidates") or []
    link.company_match_status = "weak_match" if loose else "no_verified_match"
    link.companies_house_verified = False
    link.profile_snapshot_json = classified
    link.updated_at = datetime.now(timezone.utc)
    db.commit()
    _sync_routing_after_company_verification(db, profile, actor=actor)
    return {"ok": True, "classified": classified}


def ensure_company_link(db: Session, profile: OnboardingProfile) -> OnboardingCompanyLink:
    if profile.company_link:
        return profile.company_link
    link = OnboardingCompanyLink(onboarding_profile_id=profile.id)
    db.add(link)
    db.commit()
    db.refresh(profile)
    return profile.company_link  # type: ignore


def build_summary_dict(db: Session, profile: OnboardingProfile) -> dict[str, Any]:
    return {
        "user_id": profile.user_id,
        "status": profile.status,
        "stage": profile.onboarding_stage,
        "completion_percent": profile.completion_percent,
        "acting_as": profile.acting_as,
        "business_type": profile.business_type,
        "field_count": db.query(OnboardingField).filter(OnboardingField.onboarding_profile_id == profile.id).count(),
        "pipelines": {
            r.pipeline_name: {"enabled": r.enabled, "status": r.status}
            for r in profile.pipeline_rows
        },
    }


def submit_profile(db: Session, profile: OnboardingProfile, *, actor: str = "user_api") -> OnboardingProfile:
    recompute_completion(db, profile)
    evaluate_and_save_pipelines(db, profile, actor)
    regenerate_review_flags(db, profile)
    from app.services.compliance_deadline_sync import maybe_sync_compliance_deadlines

    db.refresh(profile)
    maybe_sync_compliance_deadlines(db, profile, get_settings())
    open_flags = (
        db.query(OnboardingReviewFlag)
        .filter(
            OnboardingReviewFlag.onboarding_profile_id == profile.id,
            OnboardingReviewFlag.resolved.is_(False),
        )
        .count()
    )
    critical = (
        db.query(OnboardingReviewFlag)
        .filter(
            OnboardingReviewFlag.onboarding_profile_id == profile.id,
            OnboardingReviewFlag.resolved.is_(False),
            OnboardingReviewFlag.severity == "critical",
        )
        .count()
    )
    if critical:
        profile.status = "blocked_missing_critical_data"
    elif open_flags:
        profile.status = "complete_with_review_flags"
    elif profile.completion_percent >= 95:
        profile.status = "complete"
    else:
        profile.status = "in_progress"
    profile.summary_json = build_summary_dict(db, profile)
    profile.onboarding_stage = "completed"
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_event(db, profile, "onboarding_completed", "user" if actor == "user_api" else "onboarding_agent", actor, {})
    db.commit()
    return profile


def onboarding_context_for_prompt(db: Session, user_id: str) -> str:
    p = db.query(OnboardingProfile).filter(OnboardingProfile.user_id == user_id).one_or_none()
    if not p:
        return ""
    snap = build_summary_dict(db, p)
    routing = build_routing_snapshot(db, p)
    link = p.company_link
    company_hint = ""
    if link and link.companies_house_verified and link.matched_company_number:
        company_hint = (
            f"\nOnboarding-verified company number (prefer for compliance tools when applicable): "
            f"{link.matched_company_number} ({link.matched_company_name})."
        )
    return (
        "[Structured onboarding context — do not overwrite verified onboarding in chat; suggest review flags instead]\n"
        + json.dumps(snap, default=str)
        + "\nRouting snapshot keys: "
        + json.dumps({k: routing.get(k) for k in list(routing)[:15]}, default=str)
        + company_hint
    )
