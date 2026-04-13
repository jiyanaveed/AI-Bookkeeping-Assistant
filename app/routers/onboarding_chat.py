"""Optional LLM turn for onboarding clarification (REST + agent tools)."""

from __future__ import annotations

from agents import Runner
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.onboarding_agent_def import build_onboarding_agent
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.schemas.onboarding_api import OnboardingAgentMessage
from app.services import onboarding_service as onb
from app.tools.onboarding_tools import build_onboarding_tools

router = APIRouter(tags=["onboarding"])


@router.post("/v1/onboarding/{user_id}/agent-turn")
async def onboarding_agent_turn(
    user_id: str,
    body: OnboardingAgentMessage,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(None),
) -> dict:
    assert_path_user_matches(user_id, db, authorization)
    if not settings.openai_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured.",
        )
    profile = onb.ensure_profile(db, user_id)
    tools = build_onboarding_tools(db, profile, settings)
    agent = build_onboarding_agent(tools)
    result = await Runner.run(agent, body.message)
    reply = result.final_output if isinstance(result.final_output, str) else str(result.final_output)
    db.refresh(profile)
    return {"reply": reply, "completion_percent": profile.completion_percent, "status": profile.status}
