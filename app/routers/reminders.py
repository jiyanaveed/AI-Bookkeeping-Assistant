"""REST CRUD for reminders — agent remains authoritative for conversational creates."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.domain.reminder_channels import InvalidChannelError, normalize_reminder_channel
from app.models.db_models import ComplianceDeadline, Reminder, User
from app.schemas.reminders import (
    ComplianceBoardResponse,
    ComplianceDeadlineRead,
    ReminderCreate,
    ReminderRead,
    ReminderUpdate,
)
from app.services.compliance_deadline_sync import offset_label

router = APIRouter(tags=["reminders"])


def _ensure_user(db: Session, user_id: str) -> None:
    if db.get(User, user_id) is None:
        db.add(User(id=user_id))
        db.commit()


def _to_read(r: Reminder) -> ReminderRead:
    cd = r.compliance_deadline
    off = r.schedule_offset_days
    return ReminderRead(
        id=r.id,
        user_id=r.user_id,
        title=r.title or r.reminder_type,
        reminder_type=r.reminder_type,
        reminder_date=r.reminder_date,
        channel=r.channel,
        status=r.status,
        company_id=r.company_id,
        company_name=r.company.company_name if r.company else None,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        origin=r.origin or "manual",
        schedule_offset_days=off,
        schedule_offset_label=offset_label(off) if off is not None else None,
        compliance_deadline_id=r.compliance_deadline_id,
        deadline_kind=cd.deadline_kind if cd else None,
        compliance_due_date=cd.due_date if cd else None,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/v1/reminders/compliance-board", response_model=ComplianceBoardResponse)
def compliance_board(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> ComplianceBoardResponse:
    assert_path_user_matches(user_id, db, authorization)
    dls = (
        db.query(ComplianceDeadline)
        .options(joinedload(ComplianceDeadline.company))
        .filter(ComplianceDeadline.user_id == user_id)
        .order_by(ComplianceDeadline.due_date.asc())
        .all()
    )
    deadlines = [
        ComplianceDeadlineRead(
            id=d.id,
            user_id=d.user_id,
            company_id=d.company_id,
            company_number=d.company.company_number if d.company else None,
            company_name=d.company.company_name if d.company else None,
            deadline_kind=d.deadline_kind,
            due_date=d.due_date,
            title=d.title,
            source=d.source,
            fetched_at=d.fetched_at,
        )
        for d in dls
    ]
    manual = (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.origin == "manual", Reminder.status != "cancelled")
        .count()
    )
    auto = (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.origin == "compliance_auto", Reminder.status != "cancelled")
        .count()
    )
    note = None
    if not deadlines:
        note = (
            "No compliance deadlines stored yet. After onboarding verifies your company at Companies House "
            "and enables the reminders pipeline, deadlines sync automatically."
        )
    return ComplianceBoardResponse(
        deadlines=deadlines,
        manual_reminder_count=manual,
        auto_reminder_count=auto,
        note=note,
    )


@router.get("/v1/reminders", response_model=list[ReminderRead])
def list_reminders(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> list[ReminderRead]:
    assert_path_user_matches(user_id, db, authorization)
    rows = (
        db.query(Reminder)
        .options(
            joinedload(Reminder.company),
            joinedload(Reminder.compliance_deadline),
        )
        .filter(Reminder.user_id == user_id)
        .order_by(Reminder.reminder_date.asc(), Reminder.created_at.asc())
        .all()
    )
    return [_to_read(r) for r in rows]


@router.post("/v1/reminders", response_model=ReminderRead)
def create_reminder_api(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> ReminderRead:
    assert_path_user_matches(payload.user_id, db, authorization)
    _ensure_user(db, payload.user_id)
    try:
        ch = normalize_reminder_channel(payload.channel)
    except InvalidChannelError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    r = Reminder(
        user_id=payload.user_id,
        company_id=payload.company_id,
        title=payload.title,
        reminder_type=payload.reminder_type,
        reminder_date=payload.reminder_date,
        channel=ch,
        status=payload.status,
        origin="manual",
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    r = (
        db.query(Reminder)
        .options(joinedload(Reminder.company), joinedload(Reminder.compliance_deadline))
        .filter(Reminder.id == r.id)
        .one()
    )
    return _to_read(r)


@router.patch("/v1/reminders/{reminder_id}", response_model=ReminderRead)
def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> ReminderRead:
    assert_path_user_matches(user_id, db, authorization)
    r = db.get(Reminder, reminder_id)
    if r is None or r.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    if payload.title is not None:
        r.title = payload.title
    if payload.reminder_type is not None:
        r.reminder_type = payload.reminder_type
    if payload.reminder_date is not None:
        r.reminder_date = payload.reminder_date
    if payload.channel is not None:
        try:
            r.channel = normalize_reminder_channel(payload.channel)
        except InvalidChannelError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if payload.status is not None:
        r.status = payload.status
    r.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    r = (
        db.query(Reminder)
        .options(joinedload(Reminder.company), joinedload(Reminder.compliance_deadline))
        .filter(Reminder.id == r.id)
        .one()
    )
    return _to_read(r)


@router.post("/v1/reminders/{reminder_id}/cancel", response_model=ReminderRead)
def cancel_reminder(
    reminder_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> ReminderRead:
    assert_path_user_matches(user_id, db, authorization)
    r = db.get(Reminder, reminder_id)
    if r is None or r.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    r.status = "cancelled"
    r.updated_at = datetime.now(timezone.utc)
    db.commit()
    r = (
        db.query(Reminder)
        .options(joinedload(Reminder.company), joinedload(Reminder.compliance_deadline))
        .filter(Reminder.id == r.id)
        .one()
    )
    return _to_read(r)
