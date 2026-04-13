"""Orchestrate chat: persist messages, run Supervisor with Compliance + Bookkeeping specialists."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple

from agents import Runner
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload

from app.agents.bookkeeping import build_bookkeeping_agent
from app.agents.compliance import build_compliance_agent
from app.agents.supervisor import build_supervisor
from app.config.settings import Settings
from app.models.db_models import Conversation, Message, MessageAttachment, Upload, User
from app.services.chat_timing import ChatTiming, chat_timing_var
from app.services.companies_house import CompaniesHouseClient
from app.services import onboarding_service as onb
from app.services import transaction_service as tx_svc
from app.services.spend_fast_parse import try_parse_spend_amount
from app.tools.bookkeeping_tools import build_bookkeeping_tools
from app.tools.compliance_tools import build_compliance_tools


class ChatResult(NamedTuple):
    reply: str
    user_id: str
    conversation_id: str


def _ensure_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _ensure_conversation(db: Session, user_id: str, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found for this user.",
            )
        return conv
    conv = Conversation(user_id=user_id, channel="api")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _build_prompt(db: Session, conversation_id: str) -> str:
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(40)
        .options(joinedload(Message.file_links).joinedload(MessageAttachment.upload))
        .all()
    )
    lines: list[str] = []
    for m in rows:
        if m.sender_type == "user":
            names: list[str] = []
            upload_ids: list[str] = []
            for link in m.file_links:
                u = link.upload
                names.append(f"{u.original_filename} ({u.content_type or 'unknown'})")
                upload_ids.append(u.id)
            intent_note = " [Recorded as spending]" if getattr(m, "intent", None) == "spending" else ""
            if names:
                suffix = (
                    f" [Attached {len(names)} file(s): {', '.join(names)}. "
                    f"Upload IDs for receipt tools: {', '.join(upload_ids)}.]"
                )
            else:
                suffix = ""
            lines.append(f"user: {m.message_text}{intent_note}{suffix}")
        elif m.sender_type == "assistant":
            who = m.agent_name or "assistant"
            lines.append(f"{who}: {m.message_text}")
        else:
            lines.append(f"{m.sender_type}: {m.message_text}")
    return "\n".join(lines)


async def process_chat(
    db: Session,
    settings: Settings,
    *,
    message: str,
    user_id: str,
    conversation_id: str | None,
    attachment_ids: list[str] | None = None,
    message_intent: str | None = None,
    timing: ChatTiming | None = None,
) -> ChatResult:
    timing = timing or ChatTiming()

    t_intent = timing.span_start("intent_detection")
    intent_val: str | None = None
    if (message_intent or "").strip().lower() == "spending":
        intent_val = "spending"
    timing.span_end("intent_detection", t_intent)

    _ensure_user(db, user_id)
    conv = _ensure_conversation(db, user_id, conversation_id)

    msg = Message(
        conversation_id=conv.id,
        sender_type="user",
        agent_name=None,
        message_text=message,
        intent=intent_val,
    )
    db.add(msg)
    db.flush()

    seen: set[str] = set()
    for raw_id in attachment_ids or []:
        aid = (raw_id or "").strip()
        if not aid or aid in seen:
            continue
        seen.add(aid)
        up = db.get(Upload, aid)
        if up is None or up.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown attachment id for this user: {aid}",
            )
        db.add(MessageAttachment(message_id=msg.id, upload_id=up.id))

    conv.updated_at = datetime.now(timezone.utc)
    t_dbu = timing.span_start("db_write")
    db.commit()
    timing.span_end("db_write", t_dbu)

    has_attachments = bool(seen)

    # Fast path: spending + no attachments + single obvious amount/currency (no receipt / LLM)
    if intent_val == "spending" and not has_attachments:
        t_te = timing.span_start("transaction_extraction")
        parsed = try_parse_spend_amount(message)
        if parsed is None:
            timing.span_end("transaction_extraction", t_te)
        else:
            amount, currency = parsed
            desc = (message or "").strip()
            if len(desc) > 1024:
                desc = desc[:1021] + "..."
            row = tx_svc.create_transaction_record(
                db,
                user_id=user_id,
                amount=amount,
                currency=currency,
                description=desc or None,
                txn_date=None,
                source="chat_fast",
                message_id=msg.id,
                conversation_id=conv.id,
                receipt_id=None,
                category=None,
            )
            timing.span_end("transaction_extraction", t_te)
            ref = row.reference_code or ""
            reply = (
                f"Recorded spend **{ref}**: {amount:.2f} {currency}. "
                f"I saved this from your message without calling the full assistant pipeline."
            )
            t_dbr = timing.span_start("db_write")
            db.add(
                Message(
                    conversation_id=conv.id,
                    sender_type="assistant",
                    agent_name="Bookkeeping",
                    message_text=reply,
                )
            )
            conv.updated_at = datetime.now(timezone.utc)
            try:
                db.commit()
            except (IntegrityError, OperationalError):
                db.rollback()
                raise
            timing.span_end("db_write", t_dbr)
            timing.log_summary(fast_path=True)
            return ChatResult(reply=reply, user_id=user_id, conversation_id=conv.id)

    if not settings.openai_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured.",
        )

    spending_hint = ""
    if intent_val == "spending":
        spending_hint = (
            "[Instructions for you, Supervisor]\n"
            "The user marked this message as spending-related. Delegate to bookkeeping_specialist when they "
            "want to log spend, extract a receipt, or list transactions.\n\n"
        )

    attachment_hint = ""
    if attachment_ids:
        clean = [a.strip() for a in attachment_ids if (a or "").strip()]
        if clean:
            attachment_hint = (
                "[Attachment context]\n"
                f"This user message includes upload_id values: {', '.join(clean)}. "
                "For receipt photos, the bookkeeping specialist can call extract_receipt_from_upload with one of these IDs.\n\n"
            )

    t_cr = timing.span_start("conversation_reload")
    onboarding_ctx = onb.onboarding_context_for_prompt(db, user_id)
    prompt = _build_prompt(db, conv.id)
    if onboarding_ctx:
        prompt = f"{onboarding_ctx}\n\n---\n\n{prompt}"

    prompt = f"{spending_hint}{attachment_hint}{prompt}"
    timing.span_end("conversation_reload", t_cr)

    ch_client = CompaniesHouseClient(settings.companies_house_api_key)
    tools = build_compliance_tools(
        db,
        conversation_id=conv.id,
        user_id=user_id,
        client=ch_client,
    )
    compliance = build_compliance_agent(tools)
    bk_tools = build_bookkeeping_tools(
        db,
        conversation_id=conv.id,
        user_id=user_id,
        settings=settings,
        latest_user_message_id=msg.id,
    )
    bookkeeping = build_bookkeeping_agent(bk_tools)
    supervisor = build_supervisor(compliance, bookkeeping)

    token = chat_timing_var.set(timing)
    try:
        t_llm = timing.span_start("llm")
        try:
            result = await Runner.run(supervisor, prompt)
        except Exception:
            db.rollback()
            raise
        finally:
            timing.span_end("llm", t_llm)
    finally:
        chat_timing_var.reset(token)

    reply = result.final_output if isinstance(result.final_output, str) else str(result.final_output)

    t_dbr = timing.span_start("db_write")
    db.add(
        Message(
            conversation_id=conv.id,
            sender_type="assistant",
            agent_name="Supervisor",
            message_text=reply,
        )
    )
    conv.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise
    timing.span_end("db_write", t_dbr)

    timing.log_summary(fast_path=False)
    return ChatResult(reply=reply, user_id=user_id, conversation_id=conv.id)
