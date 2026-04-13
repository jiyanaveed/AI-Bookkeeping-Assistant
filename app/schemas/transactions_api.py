from datetime import date

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=36)
    amount: float
    currency: str = Field(default="GBP", max_length=16)
    description: str | None = Field(None, max_length=1024)
    txn_date: date | None = None
    category: str | None = Field(None, max_length=256)
    source: str = Field(default="api", max_length=128)


class TransactionRead(BaseModel):
    id: str
    reference_code: str | None
    amount: float | None
    currency: str | None
    description: str | None
    txn_date: str | None
    source: str | None
    category: str | None
    message_id: str | None
    conversation_id: str | None
    receipt_id: str | None
    created_at: str | None
