from typing import Any

from pydantic import BaseModel, Field


class OnboardingFieldIn(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=128)
    value_text: str | None = None
    value_json: list[Any] | dict[str, Any] | None = None
    source_type: str = Field(default="user_provided")
    verification_status: str = Field(default="unverified")


class OnboardingBatchUpdate(BaseModel):
    fields: list[OnboardingFieldIn]


class VerifyCompanyBody(BaseModel):
    query: str = Field(..., min_length=1)


class EvaluateRoutingBody(BaseModel):
    """Optional form sync: when present, fields are upserted before routing reads the DB snapshot."""

    fields: list[OnboardingFieldIn] = Field(default_factory=list)


class OnboardingAgentMessage(BaseModel):
    message: str = Field(..., min_length=1)
