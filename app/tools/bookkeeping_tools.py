"""Bookkeeping tools: transactions, receipt vision — used by Bookkeeping specialist agent."""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from agents import function_tool
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.services import receipt_extraction, transaction_service as tx_svc
from app.services.chat_timing import get_chat_timing
from app.tools.tool_logging import log_tool_call

AGENT_NAME = "Bookkeeping"


def build_bookkeeping_tools(
    db: Session,
    *,
    conversation_id: str,
    user_id: str,
    settings: Settings,
    latest_user_message_id: str | None,
) -> list[Any]:
    """Tools capture user_id and the current user message for provenance."""

    @function_tool
    def list_saved_transactions(limit: int = 50) -> dict[str, Any]:
        inp = {"limit": limit}
        rows = tx_svc.list_transactions_for_user(db, user_id, limit=min(max(limit, 1), 200))
        out = {
            "transactions": [tx_svc.transaction_to_dict(t) for t in rows],
            "count": len(rows),
        }
        log_tool_call(
            db,
            conversation_id=conversation_id,
            agent_name=AGENT_NAME,
            tool_name="list_saved_transactions",
            tool_input=inp,
            tool_output=out,
            success=True,
        )
        db.commit()
        return out

    @function_tool
    def create_spend_record(
        amount: float,
        currency: str = "GBP",
        description: str | None = None,
        txn_date: str | None = None,
        receipt_id: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        _t_tool = time.perf_counter()
        inp = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "txn_date": txn_date,
            "receipt_id": receipt_id,
            "category": category,
        }
        try:
            parsed_date: date | None = None
            if txn_date:
                parsed_date = date.fromisoformat(str(txn_date)[:10])
        except ValueError:
            out = {"ok": False, "error": "txn_date must be YYYY-MM-DD if provided."}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_spend_record",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            db.commit()
            ct = get_chat_timing()
            if ct:
                ct.add_transaction_extraction_nested_ms((time.perf_counter() - _t_tool) * 1000.0)
            return out
        try:
            src = "chat_vision" if receipt_id else "chat_manual"
            t = tx_svc.create_transaction_record(
                db,
                user_id=user_id,
                amount=float(amount),
                currency=currency or "GBP",
                description=description,
                txn_date=parsed_date,
                source=src,
                message_id=latest_user_message_id,
                conversation_id=conversation_id,
                receipt_id=receipt_id,
                category=category,
            )
            out = {"ok": True, **tx_svc.transaction_to_dict(t)}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_spend_record",
                tool_input=inp,
                tool_output=out,
                success=True,
            )
            db.commit()
            ct = get_chat_timing()
            if ct:
                ct.add_transaction_extraction_nested_ms((time.perf_counter() - _t_tool) * 1000.0)
            return out
        except Exception as e:
            out = {"ok": False, "error": str(e)}
            log_tool_call(
                db,
                conversation_id=conversation_id,
                agent_name=AGENT_NAME,
                tool_name="create_spend_record",
                tool_input=inp,
                tool_output=out,
                success=False,
            )
            db.commit()
            ct = get_chat_timing()
            if ct:
                ct.add_transaction_extraction_nested_ms((time.perf_counter() - _t_tool) * 1000.0)
            return out

    @function_tool
    def extract_receipt_from_upload(upload_id: str) -> dict[str, Any]:
        _t_tool = time.perf_counter()
        inp = {"upload_id": upload_id}
        out = receipt_extraction.extract_receipt_from_upload(
            db,
            settings,
            user_id=user_id,
            upload_id=upload_id.strip(),
            message_id=latest_user_message_id,
        )
        log_tool_call(
            db,
            conversation_id=conversation_id,
            agent_name=AGENT_NAME,
            tool_name="extract_receipt_from_upload",
            tool_input=inp,
            tool_output=out,
            success=bool(out.get("ok")),
        )
        db.commit()
        ct = get_chat_timing()
        if ct:
            ct.add_transaction_extraction_nested_ms((time.perf_counter() - _t_tool) * 1000.0)
        return out

    return [list_saved_transactions, create_spend_record, extract_receipt_from_upload]
