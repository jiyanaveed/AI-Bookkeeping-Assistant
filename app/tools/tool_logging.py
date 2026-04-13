"""Persist tool invocations for auditability."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.db_models import ToolCallLog


def json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(x) for x in obj]
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return {"repr": str(obj)}


def log_tool_call(
    db: Session,
    *,
    conversation_id: str,
    agent_name: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: Any,
    success: bool,
) -> None:
    row = ToolCallLog(
        conversation_id=conversation_id,
        agent_name=agent_name,
        tool_name=tool_name,
        tool_input_json=json_safe(tool_input),
        tool_output_json=json_safe(tool_output),
        success=success,
    )
    try:
        db.add(row)
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise
