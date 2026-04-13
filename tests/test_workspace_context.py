"""Workspace header copy built from onboarding (single entity per user)."""

from app.services import onboarding_service as onb


def test_display_line_verified_limited_company() -> None:
    s = onb._workspace_display_line(
        business_type="limited_company",
        acting_as=None,
        companies_house_verified=True,
        company_name="ACME LTD",
        company_number="12345678",
    )
    assert s == "Active company: ACME LTD · 12345678"


def test_display_line_limited_unverified() -> None:
    s = onb._workspace_display_line(
        business_type="limited_company",
        acting_as=None,
        companies_house_verified=False,
        company_name=None,
        company_number=None,
    )
    assert "Limited company" in s
    assert "Companies House" in s


def test_display_line_sole_trader() -> None:
    s = onb._workspace_display_line(
        business_type="sole_trader",
        acting_as=None,
        companies_house_verified=False,
        company_name=None,
        company_number=None,
    )
    assert "Sole trader" in s
