import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    companies: Mapped[list["Company"]] = relationship(back_populates="user")
    compliance_deadlines: Mapped[list["ComplianceDeadline"]] = relationship(back_populates="user")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    uploads: Mapped[list["Upload"]] = relationship(back_populates="user")
    onboarding_profile: Mapped["OnboardingProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthSession(Base):
    """Opaque bearer token sessions (v1 demo auth — swap for JWT/OAuth later)."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship(back_populates="auth_sessions")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    company_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_number: Mapped[str] = mapped_column(String(32), index=True)
    company_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    incorporation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_office_address: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    sic_codes_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    accounts_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmation_statement_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="companies")
    compliance_deadlines: Mapped[list["ComplianceDeadline"]] = relationship(back_populates="company")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="company")


class ComplianceDeadline(Base):
    """Statutory / compliance due dates (e.g. from Companies House), one row per kind per company."""

    __tablename__ = "compliance_deadlines"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "company_id",
            "deadline_kind",
            name="uq_compliance_deadline_user_co_kind",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), index=True)
    deadline_kind: Mapped[str] = mapped_column(String(64), index=True)
    due_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="companies_house")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="compliance_deadlines")
    company: Mapped["Company"] = relationship(back_populates="compliance_deadlines")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="compliance_deadline")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("companies.id"), nullable=True)
    compliance_deadline_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("compliance_deadlines.id"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reminder_type: Mapped[str] = mapped_column(String(128))
    reminder_date: Mapped[date] = mapped_column(Date)
    channel: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="scheduled")
    origin: Mapped[str] = mapped_column(String(32), default="manual")
    schedule_offset_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="reminders")
    company: Mapped["Company | None"] = relationship(back_populates="reminders")
    compliance_deadline: Mapped["ComplianceDeadline | None"] = relationship(back_populates="reminders")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(64), default="api")
    external_thread_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")
    tool_call_logs: Mapped[list["ToolCallLog"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(32))  # user | assistant | system
    agent_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message_text: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    file_links: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(128))
    tool_name: Mapped[str] = mapped_column(String(256))
    tool_input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_output_json: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="tool_call_logs")


class Upload(Base):
    """Binary upload metadata: local disk (storage_provider=local) or Supabase Storage object key."""

    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    # Local: path under upload_dir. Supabase: object path inside bucket (same string shape: user_id/id_filename).
    storage_rel_path: Mapped[str] = mapped_column(String(1024))
    storage_provider: Mapped[str] = mapped_column(String(32), default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship(back_populates="uploads")
    message_links: Mapped[list["MessageAttachment"]] = relationship(back_populates="upload")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"
    __table_args__ = (UniqueConstraint("message_id", "upload_id", name="uq_message_upload"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), index=True)
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("uploads.id"), index=True)

    message: Mapped["Message"] = relationship(back_populates="file_links")
    upload: Mapped["Upload"] = relationship(back_populates="message_links")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    upload_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("uploads.id"), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("messages.id"), nullable=True, index=True)
    file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(512), nullable=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    reference_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("messages.id"), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=True, index=True)
    receipt_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("receipts.id"), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    txn_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    category_confidence: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class OnboardingProfile(Base):
    __tablename__ = "onboarding_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="not_started")
    acting_as: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    onboarding_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completion_percent: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="onboarding_profile")
    fields: Mapped[list["OnboardingField"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    company_link: Mapped["OnboardingCompanyLink | None"] = relationship(
        back_populates="profile",
        uselist=False,
        cascade="all, delete-orphan",
    )
    review_flags: Mapped[list["OnboardingReviewFlag"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    pipeline_rows: Mapped[list["PipelineStatus"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["OnboardingEvent"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class OnboardingField(Base):
    __tablename__ = "onboarding_fields"
    __table_args__ = (UniqueConstraint("onboarding_profile_id", "field_name", name="uq_onb_field"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    onboarding_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("onboarding_profiles.id"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(128), index=True)
    field_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_value_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="user_provided")
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_by_agent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    profile: Mapped["OnboardingProfile"] = relationship(back_populates="fields")


class OnboardingCompanyLink(Base):
    __tablename__ = "onboarding_company_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    onboarding_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("onboarding_profiles.id"), unique=True, index=True
    )
    company_name_input: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_number_input: Mapped[str | None] = mapped_column(String(32), nullable=True)
    matched_company_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    matched_company_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company_match_status: Mapped[str] = mapped_column(String(32), default="not_attempted")
    companies_house_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    profile: Mapped["OnboardingProfile"] = relationship(back_populates="company_link")


class OnboardingReviewFlag(Base):
    __tablename__ = "onboarding_review_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    onboarding_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("onboarding_profiles.id"), index=True
    )
    flag_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    message: Mapped[str] = mapped_column(Text)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pipeline_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped["OnboardingProfile"] = relationship(back_populates="review_flags")


class PipelineStatus(Base):
    __tablename__ = "pipeline_statuses"
    __table_args__ = (UniqueConstraint("onboarding_profile_id", "pipeline_name", name="uq_pipeline"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    onboarding_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("onboarding_profiles.id"), index=True
    )
    pipeline_name: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="not_applicable")
    activation_source: Mapped[str] = mapped_column(String(32), default="verified_rule")
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    profile: Mapped["OnboardingProfile"] = relationship(back_populates="pipeline_rows")


class OnboardingEvent(Base):
    __tablename__ = "onboarding_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    onboarding_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("onboarding_profiles.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_name: Mapped[str] = mapped_column(String(128))
    event_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped["OnboardingProfile"] = relationship(back_populates="events")
