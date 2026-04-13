"""Onboarding Agent tools — persist via onboarding_service only."""

from __future__ import annotations

from typing import Any

from agents import function_tool
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.models.db_models import OnboardingProfile
from app.services import onboarding_service as onb

AGENT = "OnboardingAgent"


def build_onboarding_tools(db: Session, profile: OnboardingProfile, settings: Settings) -> list[Any]:
    uid = profile.user_id

    @function_tool
    def save_onboarding_fields(fields_json: str) -> dict[str, Any]:
        """Save onboarding fields from a JSON array of objects with keys: field_name, value_text (optional), value_json (optional), source_type (optional)."""
        import json

        try:
            rows = json.loads(fields_json)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}
        if not isinstance(rows, list):
            return {"ok": False, "error": "Expected JSON array"}
        for item in rows:
            if not isinstance(item, dict) or "field_name" not in item:
                continue
            onb.upsert_field(
                db,
                profile,
                field_name=str(item["field_name"]),
                value_text=item.get("value_text"),
                value_json=item.get("value_json"),
                source_type=str(item.get("source_type", "user_provided")),
                verification_status=str(item.get("verification_status", "unverified")),
                actor="onboarding_agent",
            )
        db.refresh(profile)
        return {"ok": True, "completion_percent": profile.completion_percent}

    @function_tool
    def verify_company_for_onboarding(search_query: str) -> dict[str, Any]:
        """Run Companies House verification for the user's onboarding company search."""
        return onb.verify_company(
            db, settings, profile, name_or_number=search_query, actor=AGENT
        )

    @function_tool
    def recalculate_onboarding_routing() -> dict[str, Any]:
        """Re-evaluate pipeline activation from stored onboarding fields; refresh review flags."""
        onb.evaluate_and_save_pipelines(db, profile, actor=AGENT)
        onb.regenerate_review_flags(db, profile)
        db.commit()
        db.refresh(profile)
        return {
            "ok": True,
            "pipelines": [
                {"name": r.pipeline_name, "enabled": r.enabled, "status": r.status}
                for r in sorted(profile.pipeline_rows, key=lambda x: x.pipeline_name)
            ],
        }

    return [save_onboarding_fields, verify_company_for_onboarding, recalculate_onboarding_routing]
