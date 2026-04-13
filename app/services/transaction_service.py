"""Spend / transaction rows with human reference codes."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.db_models import Receipt, Transaction


def next_reference_code(db: Session, user_id: str) -> str:
    """Collision-resistant spend reference, unique per user when combined with partial DB index."""
    from datetime import date as date_cls

    d = date_cls.today().isoformat().replace("-", "")
    for _ in range(12):
        suffix = secrets.token_hex(2).upper()
        code = f"SPEND-{d}-{suffix}"
        exists = (
            db.query(Transaction.id)
            .filter(Transaction.user_id == user_id, Transaction.reference_code == code)
            .first()
        )
        if exists is None:
            return code
    return f"SPEND-{d}-{secrets.token_hex(4).upper()}"


def create_transaction_record(
    db: Session,
    *,
    user_id: str,
    amount: float,
    currency: str = "GBP",
    description: str | None = None,
    txn_date: date | None = None,
    source: str = "api",
    message_id: str | None = None,
    conversation_id: str | None = None,
    receipt_id: str | None = None,
    category: str | None = None,
    reference_code: str | None = None,
) -> Transaction:
    ref = reference_code or next_reference_code(db, user_id)
    row = Transaction(
        user_id=user_id,
        reference_code=ref,
        amount=amount,
        currency=(currency or "GBP")[:16],
        description=(description or "")[:1024] if description else None,
        txn_date=txn_date,
        source=source[:128] if source else None,
        message_id=message_id,
        conversation_id=conversation_id,
        receipt_id=receipt_id,
        category=category[:256] if category else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def link_transaction_to_receipt(db: Session, transaction: Transaction, receipt: Receipt) -> None:
    transaction.receipt_id = receipt.id
    receipt.updated_at = datetime.now(timezone.utc)
    transaction.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(transaction)


def list_transactions_for_user(db: Session, user_id: str, *, limit: int = 200) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )


def transaction_to_dict(t: Transaction) -> dict[str, Any]:
    return {
        "id": t.id,
        "reference_code": t.reference_code,
        "amount": float(t.amount) if t.amount is not None else None,
        "currency": t.currency,
        "description": t.description,
        "txn_date": t.txn_date.isoformat() if t.txn_date else None,
        "source": t.source,
        "category": t.category,
        "message_id": t.message_id,
        "conversation_id": t.conversation_id,
        "receipt_id": t.receipt_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
