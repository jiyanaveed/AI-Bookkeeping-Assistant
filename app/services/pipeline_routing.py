"""Pipeline activation rules from specs/09_PIPELINE_ROUTING_RULES.md — deterministic, testable."""

from __future__ import annotations

from typing import Any

PIPELINE_NAMES = (
    "companies_house",
    "company_formation",
    "self_assessment",
    "property_income",
    "vat",
    "payroll",
    "mtd_income_tax",
    "reminders",
)

VAT_THRESHOLD_HINT = 85_000.0


def _txt(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def _parse_turnover(snapshot: dict[str, Any]) -> float | None:
    raw = snapshot.get("estimated_12_month_taxable_turnover")
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", ""))
    except ValueError:
        return None


def _income_types(snapshot: dict[str, Any]) -> list[str]:
    v = snapshot.get("income_types")
    if v is None:
        return []
    if isinstance(v, list):
        return [_txt(x) for x in v]
    if isinstance(v, str):
        return [_txt(x) for x in v.split(",") if x.strip()]
    return []


def compute_pipeline_decisions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """snapshot: flat field_name -> value. Returns rows for PipelineStatus upsert."""
    bt = _txt(snapshot.get("business_type"))
    reg = _txt(snapshot.get("company_registration_status"))
    match_status = _txt(snapshot.get("company_match_status"))
    ch_verified = bool(snapshot.get("companies_house_verified"))
    income = _income_types(snapshot)
    sa_reg = _txt(snapshot.get("self_assessment_registered"))
    vat_st = _txt(snapshot.get("vat_status"))
    payroll = _txt(snapshot.get("payroll_status"))
    turnover = _parse_turnover(snapshot)
    channel = _txt(snapshot.get("preferred_reminder_channel"))
    email = _txt(snapshot.get("email"))
    phone = _txt(snapshot.get("phone_number"))
    first_payday = _txt(snapshot.get("first_payday_date"))
    paye_avail = _txt(snapshot.get("paye_reference_available"))

    limited = bt == "limited_company"
    landlord_bt = bt in ("landlord", "sole_trader_and_landlord")
    has_rental_income = "rental_property_income" in income or landlord_bt

    by_name: dict[str, dict[str, Any]] = {}

    if limited and reg == "already_registered":
        if ch_verified and match_status == "strong_match":
            by_name["companies_house"] = {
                "pipeline_name": "companies_house",
                "enabled": True,
                "status": "active",
                "activation_source": "verified_rule",
                "reason_text": "Limited company, registered, strong Companies House match verified.",
            }
        else:
            by_name["companies_house"] = {
                "pipeline_name": "companies_house",
                "enabled": False,
                "status": "pending_verification",
                "activation_source": "verified_rule",
                "reason_text": "Company identity not strongly verified; CH pipeline not fully activated.",
                "metadata_json": {"match_status": match_status or "unknown"},
            }
    else:
        by_name["companies_house"] = {
            "pipeline_name": "companies_house",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "Not a limited-company registered path.",
        }

    if limited and reg in ("want_to_register", "registration_in_progress"):
        by_name["company_formation"] = {
            "pipeline_name": "company_formation",
            "enabled": True,
            "status": "review",
            "activation_source": "verified_rule",
            "reason_text": "Formation / registration in progress.",
        }
    else:
        by_name["company_formation"] = {
            "pipeline_name": "company_formation",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "Not in formation path.",
        }

    sa_trigger = (
        sa_reg == "yes"
        or any(
            x in income
            for x in (
                "self_employment_income",
                "rental_property_income",
                "dividends",
                "other",
                "limited_company_income",
            )
        )
        or bt in ("sole_trader", "landlord", "sole_trader_and_landlord", "partnership")
    )
    if sa_trigger:
        by_name["self_assessment"] = {
            "pipeline_name": "self_assessment",
            "enabled": True,
            "status": "review" if sa_reg == "not_sure" else "active",
            "activation_source": "inferred_rule" if sa_reg == "not_sure" else "verified_rule",
            "reason_text": "Self Assessment path indicated."
            + (" Uncertainty on registration." if sa_reg == "not_sure" else ""),
        }
    else:
        by_name["self_assessment"] = {
            "pipeline_name": "self_assessment",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "No SA trigger.",
        }

    if has_rental_income:
        by_name["property_income"] = {
            "pipeline_name": "property_income",
            "enabled": True,
            "status": "monitor",
            "activation_source": "verified_rule",
            "reason_text": "Property / rental income indicated.",
        }
    else:
        by_name["property_income"] = {
            "pipeline_name": "property_income",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "No property income.",
        }

    if vat_st == "vat_registered":
        by_name["vat"] = {
            "pipeline_name": "vat",
            "enabled": True,
            "status": "active",
            "activation_source": "verified_rule",
            "reason_text": "VAT registered.",
        }
    elif turnover is not None and turnover >= VAT_THRESHOLD_HINT:
        by_name["vat"] = {
            "pipeline_name": "vat",
            "enabled": True,
            "status": "monitor",
            "activation_source": "inferred_rule",
            "reason_text": "Turnover estimate suggests VAT threshold monitoring.",
        }
    elif vat_st == "monitor_threshold":
        by_name["vat"] = {
            "pipeline_name": "vat",
            "enabled": True,
            "status": "monitor",
            "activation_source": "verified_rule",
            "reason_text": "User requested VAT threshold monitoring.",
        }
    else:
        by_name["vat"] = {
            "pipeline_name": "vat",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "No VAT signal.",
        }

    payroll_trigger = payroll in ("has_employees", "director_only") or bool(first_payday) or paye_avail == "yes"
    if payroll_trigger:
        by_name["payroll"] = {
            "pipeline_name": "payroll",
            "enabled": True,
            "status": "review",
            "activation_source": "verified_rule",
            "reason_text": "Payroll / PAYE signals.",
        }
    else:
        by_name["payroll"] = {
            "pipeline_name": "payroll",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "No payroll signals.",
        }

    mtd_trigger = (
        "self_employment_income" in income
        or "rental_property_income" in income
        or "limited_company_income" in income
        or landlord_bt
        or bt == "sole_trader"
    )
    if mtd_trigger:
        by_name["mtd_income_tax"] = {
            "pipeline_name": "mtd_income_tax",
            "enabled": True,
            "status": "review",
            "activation_source": "inferred_rule",
            "reason_text": "Possible MTD Income Tax scope.",
        }
    else:
        by_name["mtd_income_tax"] = {
            "pipeline_name": "mtd_income_tax",
            "enabled": False,
            "status": "not_applicable",
            "activation_source": "verified_rule",
            "reason_text": "No MTD IT trigger.",
        }

    if channel:
        need_email = channel == "email" and not email
        need_phone = channel == "whatsapp" and not phone
        if need_email or need_phone:
            by_name["reminders"] = {
                "pipeline_name": "reminders",
                "enabled": True,
                "status": "setup_incomplete",
                "activation_source": "verified_rule",
                "reason_text": "Channel selected but required contact detail missing.",
            }
        else:
            by_name["reminders"] = {
                "pipeline_name": "reminders",
                "enabled": True,
                "status": "active",
                "activation_source": "verified_rule",
                "reason_text": "Reminder preferences captured.",
                "metadata_json": {
                    "delivery_note": "WhatsApp/Slack external delivery remains stub_only.",
                },
            }
    else:
        by_name["reminders"] = {
            "pipeline_name": "reminders",
            "enabled": False,
            "status": "setup_incomplete",
            "activation_source": "verified_rule",
            "reason_text": "No reminder channel.",
        }

    return [by_name[n] for n in PIPELINE_NAMES]
