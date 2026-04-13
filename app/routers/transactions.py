"""User spend / transaction ledger (bookkeeping MVP)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.schemas.transactions_api import TransactionCreate, TransactionRead
from app.services import transaction_service as tx_svc

router = APIRouter(tags=["transactions"])


@router.get("/v1/transactions", response_model=list[TransactionRead])
def list_transactions(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> list[TransactionRead]:
    assert_path_user_matches(user_id, db, authorization)
    rows = tx_svc.list_transactions_for_user(db, user_id)
    return [TransactionRead(**tx_svc.transaction_to_dict(t)) for t in rows]


@router.post("/v1/transactions", response_model=TransactionRead)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> TransactionRead:
    assert_path_user_matches(payload.user_id, db, authorization)
    t = tx_svc.create_transaction_record(
        db,
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        txn_date=payload.txn_date,
        source=payload.source,
        category=payload.category,
    )
    return TransactionRead(**tx_svc.transaction_to_dict(t))
