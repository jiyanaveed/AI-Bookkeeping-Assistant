"""Lightweight SQLite column adds for existing dev DBs (no Alembic)."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def apply_sqlite_migrations(engine: Engine) -> None:
    if not str(engine.url).lower().startswith("sqlite"):
        return
    insp = inspect(engine)
    if not insp.has_table("reminders"):
        return
    cols = {c["name"] for c in insp.get_columns("reminders")}
    with engine.begin() as conn:
        if "title" not in cols:
            conn.execute(text("ALTER TABLE reminders ADD COLUMN title VARCHAR(256)"))

    if insp.has_table("users"):
        ucols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "password_hash" not in ucols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)"))

    if not insp.has_table("auth_sessions"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE auth_sessions (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        token VARCHAR(128) NOT NULL UNIQUE,
                        expires_at DATETIME NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)"))

    if not insp.has_table("compliance_deadlines"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE compliance_deadlines (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        company_id VARCHAR(36) NOT NULL,
                        deadline_kind VARCHAR(64) NOT NULL,
                        due_date DATE NOT NULL,
                        title VARCHAR(512),
                        source VARCHAR(64) NOT NULL DEFAULT 'companies_house',
                        fetched_at DATETIME NOT NULL,
                        metadata_json JSON,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(company_id) REFERENCES companies(id),
                        CONSTRAINT uq_compliance_deadline_user_co_kind
                            UNIQUE (user_id, company_id, deadline_kind)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX ix_compliance_deadlines_user_id ON compliance_deadlines (user_id)"))
            conn.execute(text("CREATE INDEX ix_compliance_deadlines_company_id ON compliance_deadlines (company_id)"))
            conn.execute(text("CREATE INDEX ix_compliance_deadlines_kind ON compliance_deadlines (deadline_kind)"))

    if insp.has_table("reminders"):
        rcols = {c["name"] for c in insp.get_columns("reminders")}
        with engine.begin() as conn:
            if "compliance_deadline_id" not in rcols:
                conn.execute(
                    text(
                        "ALTER TABLE reminders ADD COLUMN compliance_deadline_id VARCHAR(36) "
                        "REFERENCES compliance_deadlines(id)"
                    )
                )
            if "schedule_offset_days" not in rcols:
                conn.execute(text("ALTER TABLE reminders ADD COLUMN schedule_offset_days INTEGER"))
            if "origin" not in rcols:
                conn.execute(text("ALTER TABLE reminders ADD COLUMN origin VARCHAR(32) NOT NULL DEFAULT 'manual'"))

    if insp.has_table("messages"):
        mcols = {c["name"] for c in insp.get_columns("messages")}
        with engine.begin() as conn:
            if "intent" not in mcols:
                conn.execute(text("ALTER TABLE messages ADD COLUMN intent VARCHAR(64)"))

    if insp.has_table("receipts"):
        rcols = {c["name"] for c in insp.get_columns("receipts")}
        with engine.begin() as conn:
            if "upload_id" not in rcols:
                conn.execute(text("ALTER TABLE receipts ADD COLUMN upload_id VARCHAR(36)"))
            if "message_id" not in rcols:
                conn.execute(text("ALTER TABLE receipts ADD COLUMN message_id VARCHAR(36)"))

    if insp.has_table("transactions"):
        tcols = {c["name"] for c in insp.get_columns("transactions")}
        with engine.begin() as conn:
            if "reference_code" not in tcols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN reference_code VARCHAR(40)"))
            if "message_id" not in tcols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN message_id VARCHAR(36)"))
            if "conversation_id" not in tcols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN conversation_id VARCHAR(36)"))
            if "receipt_id" not in tcols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN receipt_id VARCHAR(36)"))

    # Partial unique index SQLite 3.8+: enforce unique reference per user when set
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_user_reference "
                "ON transactions (user_id, reference_code) WHERE reference_code IS NOT NULL"
            )
        )
