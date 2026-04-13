"""Fetch Companies House deadlines, persist them, and generate automatic reminder schedules."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.domain.reminder_channels import normalize_reminder_channel
from app.models.db_models import ComplianceDeadline, OnboardingProfile, Reminder, User
from app.services.companies_house import (
    CompaniesHouseClient,
    normalize_deadlines,
    normalize_profile,
)
from app.tools.compliance_tools import _load_company_row, _upsert_company_cache


# Days before statutory due date (0 = on the due date).
OFFSETS_DAYS: tuple[int, ...] = (30, 14, 7, 0)


def offset_label(days: int) -> str:
    if days == 0:
        return "due_date"
    return f"{days}_days_before"


def compute_trigger_date(due: date, offset_days: int) -> date:
    return due - timedelta(days=offset_days)


def _parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    return date.fromisoformat(s[:10])


def compliance_sync_eligible(profile: OnboardingProfile) -> bool:
    """Companies House verified + companies_house and reminders pipelines enabled."""
    link = profile.company_link
    if not link or not link.companies_house_verified or not (link.matched_company_number or "").strip():
        return False
    by_name = {r.pipeline_name: r for r in (profile.pipeline_rows or [])}
    ch = by_name.get("companies_house")
    rem = by_name.get("reminders")
    if ch is None or rem is None:
        return False
    if not ch.enabled or not rem.enabled:
        return False
    return True


def preferred_reminder_channel_for_user(db: Session, user_id: str) -> str:
    u = db.get(User, user_id)
    raw = (u.preferred_channel if u else None) or "in_app"
    try:
        return normalize_reminder_channel(raw)
    except Exception:
        return "in_app"


def sync_compliance_deadlines_for_user(
    db: Session,
    *,
    user_id: str,
    company_number: str,
    settings: Settings,
) -> dict[str, Any]:
    """
    Pull Companies House company profile, upsert Company + ComplianceDeadline rows,
    and create/update automatic Reminder rows (offsets 30, 14, 7, due date).
    """
    cn = company_number.strip().upper()
    if not settings.companies_house_api_key.strip():
        return {"ok": False, "skipped": True, "reason": "COMPANIES_HOUSE_API_KEY not configured"}

    client = CompaniesHouseClient(settings.companies_house_api_key)
    raw = client.get_company_raw(cn)
    if not raw:
        return {"ok": False, "skipped": True, "reason": "company_not_found"}

    prof = normalize_profile(raw)
    prof["company_number"] = prof.get("company_number") or cn
    _upsert_company_cache(db, user_id=user_id, profile=prof)

    co = _load_company_row(db, user_id=user_id, company_number=cn)
    if co is None:
        return {"ok": False, "skipped": True, "reason": "company_row_missing"}

    dl = normalize_deadlines(prof)
    upcoming = dl.get("upcoming_deadlines") or []
    now = datetime.now(timezone.utc)
    channel = preferred_reminder_channel_for_user(db, user_id)

    deadline_rows: list[ComplianceDeadline] = []
    for item in upcoming:
        kind = str(item.get("kind") or "").strip()
        due = _parse_date(item.get("due_date"))
        if not kind or not due:
            continue
        label = item.get("label") or kind.replace("_", " ").title()

        row = (
            db.query(ComplianceDeadline)
            .filter(
                ComplianceDeadline.user_id == user_id,
                ComplianceDeadline.company_id == co.id,
                ComplianceDeadline.deadline_kind == kind,
            )
            .one_or_none()
        )
        if row is None:
            row = ComplianceDeadline(
                user_id=user_id,
                company_id=co.id,
                deadline_kind=kind,
                due_date=due,
                title=label,
                source="companies_house",
                fetched_at=now,
                metadata_json={"profile_snippet": {"overdue": dl.get("overdue_flags")}},
            )
            db.add(row)
        else:
            row.due_date = due
            row.title = label
            row.fetched_at = now
            row.metadata_json = {"profile_snippet": {"overdue": dl.get("overdue_flags")}}
        deadline_rows.append(row)

    db.commit()

    for row in deadline_rows:
        db.refresh(row)
        _ensure_auto_reminders_for_deadline(db, row, co.company_name or "", channel)

    db.commit()
    return {
        "ok": True,
        "deadlines_upserted": len(deadline_rows),
        "company_number": cn,
        "channel": channel,
    }


def _ensure_auto_reminders_for_deadline(
    db: Session,
    dl: ComplianceDeadline,
    company_name: str,
    channel: str,
) -> None:
    today = date.today()
    due = dl.due_date
    kind_short = dl.deadline_kind
    base_title = (dl.title or kind_short).strip()

    for offset in OFFSETS_DAYS:
        trigger = compute_trigger_date(due, offset)
        if trigger < today:
            continue

        label = offset_label(offset)
        title = (
            f"{offset} days before: {base_title}" if offset > 0 else f"Due: {base_title}"
        ).strip()
        if company_name:
            title = f"{title} ({company_name})"

        existing = (
            db.query(Reminder)
            .filter(
                Reminder.user_id == dl.user_id,
                Reminder.compliance_deadline_id == dl.id,
                Reminder.schedule_offset_days == offset,
            )
            .one_or_none()
        )

        reminder_type = f"compliance:{kind_short}"
        if existing:
            if existing.status == "cancelled":
                continue
            existing.reminder_date = trigger
            existing.channel = channel
            existing.title = title
            existing.reminder_type = reminder_type
            existing.company_id = dl.company_id
            existing.origin = "compliance_auto"
            existing.updated_at = datetime.now(timezone.utc)
            continue

        db.add(
            Reminder(
                user_id=dl.user_id,
                company_id=dl.company_id,
                compliance_deadline_id=dl.id,
                title=title,
                reminder_type=reminder_type,
                reminder_date=trigger,
                channel=channel,
                status="scheduled",
                origin="compliance_auto",
                schedule_offset_days=offset,
                entity_type="compliance_deadline",
                entity_id=dl.id,
            )
        )


def maybe_sync_compliance_deadlines(
    db: Session,
    profile: OnboardingProfile,
    settings: Settings,
) -> dict[str, Any] | None:
    if not compliance_sync_eligible(profile):
        return None
    link = profile.company_link
    assert link is not None
    num = (link.matched_company_number or "").strip().upper()
    if not num:
        return None
    return sync_compliance_deadlines_for_user(db, user_id=profile.user_id, company_number=num, settings=settings)
