from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        s = v.strip().lower()
        if "@" not in s or "." not in s.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return s


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str | None


class OnboardingGateInfo(BaseModel):
    status: str
    completion_percent: int
    can_access_app: bool
    onboarding_stage: str | None


class WorkspaceContext(BaseModel):
    """What the workspace should show for the active (onboarding) business — one profile per user today."""

    business_type: str | None = None
    acting_as: str | None = None
    primary_company_name: str | None = None
    primary_company_number: str | None = None
    companies_house_verified: bool = False
    display_line: str = ""


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    full_name: str | None
    onboarding: OnboardingGateInfo
    workspace: WorkspaceContext
