"""Compliance-facing tools: Companies House + reminders (DB)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from agents import function_tool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import Company, Reminder
from app.services.companies_house import (
    CompaniesHouseClient,
    CompaniesHouseError,
    normalize_deadlines,
    normalize_filing_history,
    normalize_profile,
)
from app.services.company_search_match import classify_company_search_results
from app.tools.tool_logging import log_tool_call

AGENT_NAME = "Compliance"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def _load_company_row(db: Session, *, user_id: str, company_number: str) -> Company | None:
    """Prefer a stable row when legacy duplicates exist (same user + company_number)."""
    with db.no_autoflush:
        return (
            db.execute(
                select(Company)
                .where(Company.user_id == user_id, Company.company_number == company_number)
                .order_by(Company.created_at.asc())
                .limit(1)
            )
            .scalars()
            .first()
        )


def _apply_company_profile(
    co: Company,
    *,
    user_id: str,
    profile: dict[str, Any],
    synced: datetime,
) -> None:
    """Idempotent in-memory update for a cached company row."""
    addr = profile.get("registered_office_address")
    sics = profile.get("sic_codes")
    co.user_id = user_id
    co.company_name = profile.get("company_name")
    co.company_number = str(profile.get("company_number", co.company_number)).strip().upper()
    co.company_status = profile.get("company_status")
    co.incorporation_date = _parse_date(profile.get("incorporation_date"))
    co.registered_office_address = addr
    co.sic_codes_json = sics
    co.accounts_due_date = _parse_date(profile.get("accounts_due_date"))
    co.confirmation_statement_due_date = _parse_date(profile.get("confirmation_statement_due_date"))
    co.last_synced_at = synced


def _upsert_company_cache(db: Session, *, user_id: str, profile: dict[str, Any]) -> None:
    num = profile.get("company_number")
    if not num:
        return
    cn = str(num).strip().upper()
    synced = datetime.now(timezone.utc)

    def _resolve_existing() -> Company | None:
        return _load_company_row(db, user_id=user_id, company_number=cn)

    co = _resolve_existing()
    if co is not None:
        _apply_company_profile(co, user_id=user_id, profile=profile, synced=synced)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            co = _resolve_existing()
            if co is None:
                raise
            _apply_company_profile(co, user_id=user_id, profile=profile, synced=synced)
            db.commit()
        return

    co = Company(user_id=user_id, company_number=cn)
    _apply_company_profile(co, user_id=user_id, profile=profile, synced=synced)
    db.add(co)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        co = _resolve_existing()
        if co is None:
            raise
        _apply_company_profile(co, user_id=user_id, profile=profile, synced=synced)
        db.commit()


def build_compliance_tools(
    db: Session,
    *,
    conversation_id: str,
    user_id: str,
    client: CompaniesHouseClient,
) -> list[Any]:
    """Build fresh tool callables per request (captures db + ids for logging)."""

    @function_tool
    def search_company_by_name(query: str) -> dict[str, Any]:
        inp = {"query": query}
        try:
            raw = client.search_companies(query)
            items = raw.get("items") or []
            out = classify_company_search_results(query, items)
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="search_company_by_name",
                tool_input=inp,
                tool_output=out,
                success=True,
            )
            return out
        except CompaniesHouseError as e:
            out = {"error": str(e), "candidates": []}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="search_company_by_name",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out
        except Exception as e:
            out = {"error": str(e), "candidates": []}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="search_company_by_name",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out

    @function_tool
    def get_company_profile(company_number: str) -> dict[str, Any]:
        inp = {"company_number": company_number}
        try:
            raw = client.get_company_raw(company_number)
            if not raw:
                out = {"error": "No company found for that company number.", "profile": None}
                log_tool_call(
                    db,
                    conversation_id=conversation_id,
                    agent_name=AGENT_NAME,
                    tool_name="get_company_profile",
                    tool_input=inp,
                    tool_output=out,
                    success=False,
                )
                return out
            profile = normalize_profile(raw)
            _upsert_company_cache(db, user_id=user_id, profile=profile)
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_profile",
                tool_input=inp,
                tool_output=profile,
                success=True,
            )
            return profile
        except CompaniesHouseError as e:
            out = {"error": str(e), "profile": None}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_profile",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out
        except Exception as e:
            out = {"error": str(e), "profile": None}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_profile",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out

    @function_tool
    def get_company_deadlines(company_number: str) -> dict[str, Any]:
        inp = {"company_number": company_number}
        try:
            raw = client.get_company_raw(company_number)
            if not raw:
                out = {"error": "No company found for that company number."}
                log_tool_call(
                    db,
                    conversation_id=conversation_id,
                    agent_name=AGENT_NAME,
                    tool_name="get_company_deadlines",
                    tool_input=inp,
                    tool_output=out,
                    success=False,
                )
                return out
            profile = normalize_profile(raw)
            _upsert_company_cache(db, user_id=user_id, profile=profile)
            deadlines = normalize_deadlines(profile)
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_deadlines",
                tool_input=inp,
                tool_output=deadlines,
                success=True,
            )
            return deadlines
        except CompaniesHouseError as e:
            out = {"error": str(e)}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_deadlines",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out
        except Exception as e:
            out = {"error": str(e)}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_deadlines",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out

    @function_tool
    def get_company_filing_history(company_number: str) -> dict[str, Any]:
        inp = {"company_number": company_number}
        try:
            raw = client.get_filing_history_raw(company_number)
            filings = normalize_filing_history(raw)
            out: dict[str, Any] = {"filings": filings}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_filing_history",
                tool_input=inp,
                tool_output=out,
                success=True,
            )
            return out
        except CompaniesHouseError as e:
            out = {"error": str(e), "filings": []}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_filing_history",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out
        except Exception as e:
            out = {"error": str(e), "filings": []}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="get_company_filing_history",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out

    @function_tool
    def create_reminder(
        entity_type: str,
        entity_id: str,
        reminder_type: str,
        reminder_date: str,
        channel: str,
        user_confirmed: bool,
    ) -> dict[str, Any]:
        """Create a reminder only after the user has explicitly confirmed (user_confirmed=true)."""
        inp = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "reminder_type": reminder_type,
            "reminder_date": reminder_date,
            "channel": channel,
            "user_confirmed": user_confirmed,
        }
        if not user_confirmed:
            out = {
                "reminder_status": "pending_confirmation",
                "reminder_id": None,
                "reason": (
                    "Confirmation is required before a reminder can be saved. "
                    "State the verified Companies House deadline you used, the reminder trigger "
                    "date (YYYY-MM-DD), entity (company number), and channel; ask the user to "
                    "confirm explicitly (e.g. 'yes'). Reminders are available—do not imply they "
                    "are unsupported. Call again with user_confirmed=true only after explicit confirmation."
                ),
            }
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_reminder",
                tool_input=inp,
                tool_output=out,
                success=True,
            )
            return out
        try:
            rd = date.fromisoformat(reminder_date[:10])
        except ValueError:
            out = {
                "reminder_status": "error",
                "reminder_id": None,
                "reason": "reminder_date must be ISO YYYY-MM-DD.",
            }
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_reminder",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            return out

        company_db_id = None
        if entity_type.lower() == "company":
            encn = entity_id.strip().upper()
            co = _load_company_row(db, user_id=user_id, company_number=encn)
            if co is not None:
                company_db_id = co.id

        rem = Reminder(
            user_id=user_id,
            company_id=company_db_id,
            title=None,
            reminder_type=reminder_type,
            reminder_date=rd,
            channel=channel,
            status="scheduled",
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(rem)
        try:
            db.commit()
            db.refresh(rem)
        except IntegrityError:
            db.rollback()
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_reminder",
                tool_input=inp,
                tool_output={
                    "reminder_status": "error",
                    "reminder_id": None,
                    "reason": "Could not save reminder due to a database conflict.",
                },
                success=False,
            )
            return {
                "reminder_status": "error",
                "reminder_id": None,
                "reason": "Could not save reminder due to a database conflict.",
            }
        out = {"reminder_status": "created", "reminder_id": rem.id}
        log_tool_call(
            db,
            conversation_id=conversation_id,
            agent_name=AGENT_NAME,
            tool_name="create_reminder",
            tool_input=inp,
            tool_output=out,
            success=True,
        )
        return out

    @function_tool
    def list_upcoming_deadlines() -> dict[str, Any]:
        inp = {"user_id": user_id}
        today = date.today()
        rows = (
            db.query(Reminder)
            .filter(
                Reminder.user_id == user_id,
                Reminder.status != "cancelled",
                Reminder.reminder_date >= today,
            )
            .order_by(Reminder.reminder_date.asc())
            .limit(50)
            .all()
        )
        upcoming = [
            {
                "reminder_id": r.id,
                "title": r.title or r.reminder_type,
                "reminder_type": r.reminder_type,
                "reminder_date": r.reminder_date.isoformat(),
                "channel": r.channel,
                "status": r.status,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
            }
            for r in rows
        ]
        out: dict[str, Any] = {"upcoming_deadlines": upcoming}
        log_tool_call(
            db,
            conversation_id=conversation_id,
            agent_name=AGENT_NAME,
            tool_name="list_upcoming_deadlines",
            tool_input=inp,
            tool_output=out,
            success=True,
        )
        return out

    return [
        search_company_by_name,
        get_company_profile,
        get_company_deadlines,
        get_company_filing_history,
        create_reminder,
        list_upcoming_deadlines,
    ]
