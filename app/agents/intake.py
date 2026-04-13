"""Intake Agent — Phase 1 partial; post-onboarding document/message extraction (not auto-routed every turn)."""

from agents import Agent

intake_agent = Agent(
    name="Intake",
    handoff_description="Structured extraction from chat and documents after onboarding.",
    instructions=(
        "You parse user messages and uploaded financial documents into structured fields. "
        "You do NOT own the core tax onboarding profile: never silently change verified onboarding "
        "data. You may suggest candidate field updates labelled user_provided or needs_review. "
        "The Onboarding Agent owns onboarding_profiles and pipeline activation. "
        "Phase 1: you are not invoked on every message—main chat uses Supervisor + Compliance."
    ),
    model="gpt-4o-mini",
)
