from datetime import date

from pydantic import BaseModel, Field


class ComplianceDeadlineRead(BaseModel):
    id: str
    user_id: str
    company_id: str
    company_number: str | None = None
    company_name: str | None = None
    deadline_kind: str
    due_date: date
    title: str | None = None
    source: str
    fetched_at: object


class ComplianceBoardResponse(BaseModel):
    deadlines: list[ComplianceDeadlineRead]
    manual_reminder_count: int
    auto_reminder_count: int
    note: str | None = None


class ReminderCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=36)
    reminder_type: str = Field(..., min_length=1, max_length=128)
    reminder_date: date
    channel: str = Field(..., min_length=1, max_length=64)
    title: str | None = Field(None, max_length=256)
    status: str = Field(default="scheduled", max_length=64)
    company_id: str | None = Field(None, max_length=36)
    entity_type: str | None = Field(None, max_length=64)
    entity_id: str | None = Field(None, max_length=128)


class ReminderUpdate(BaseModel):
    title: str | None = Field(None, max_length=256)
    reminder_type: str | None = Field(None, max_length=128)
    reminder_date: date | None = None
    channel: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=64)


class ReminderRead(BaseModel):
    id: str
    user_id: str
    title: str
    reminder_type: str
    reminder_date: date
    channel: str
    status: str
    company_id: str | None
    company_name: str | None
    entity_type: str | None
    entity_id: str | None
    origin: str = "manual"
    schedule_offset_days: int | None = None
    schedule_offset_label: str | None = None
    compliance_deadline_id: str | None = None
    deadline_kind: str | None = None
    compliance_due_date: date | None = None
    created_at: object
    updated_at: object

    model_config = {"from_attributes": False}
