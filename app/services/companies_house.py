"""Companies House REST API client — read-only lookups."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

BASE_URL = "https://api.company-information.service.gov.uk"


class CompaniesHouseError(Exception):
    pass


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CompaniesHouseClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key or ""

    def _require_key(self) -> None:
        if not self._api_key.strip():
            raise CompaniesHouseError("COMPANIES_HOUSE_API_KEY is not configured.")

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=BASE_URL, auth=(self._api_key, ""), timeout=30.0)

    def search_companies(self, query: str) -> dict[str, Any]:
        self._require_key()
        with self._client() as client:
            response = client.get("/search/companies", params={"q": query})
            if response.status_code == 401:
                raise CompaniesHouseError("Companies House API authentication failed.")
            response.raise_for_status()
            return response.json()

    def get_company_raw(self, company_number: str) -> dict[str, Any]:
        self._require_key()
        cn = company_number.strip().upper()
        with self._client() as client:
            response = client.get(f"/company/{cn}")
            if response.status_code == 404:
                return {}
            if response.status_code == 401:
                raise CompaniesHouseError("Companies House API authentication failed.")
            response.raise_for_status()
            return response.json()

    def get_filing_history_raw(self, company_number: str, items_per_page: int = 25) -> dict[str, Any]:
        self._require_key()
        cn = company_number.strip().upper()
        with self._client() as client:
            response = client.get(
                f"/company/{cn}/filing-history",
                params={"items_per_page": items_per_page},
            )
            if response.status_code == 404:
                return {"items": []}
            if response.status_code == 401:
                raise CompaniesHouseError("Companies House API authentication failed.")
            response.raise_for_status()
            return response.json()


def normalize_profile(data: dict[str, Any]) -> dict[str, Any]:
    """Map Companies House company payload to tool contract shape."""
    if not data:
        return {}

    addr = data.get("registered_office_address")
    if isinstance(addr, str):
        try:
            addr = json.loads(addr)
        except json.JSONDecodeError:
            addr = {"raw": addr}

    sics_raw = data.get("sic_codes") or []
    sic_codes: list[str] = []
    for item in sics_raw:
        if isinstance(item, dict) and item.get("sic_code"):
            sic_codes.append(str(item["sic_code"]))
        elif isinstance(item, str):
            sic_codes.append(item)

    accounts = data.get("accounts") or {}
    next_accounts = accounts.get("next_accounts") or {}
    cs = data.get("confirmation_statement") or {}

    return {
        "company_name": data.get("company_name"),
        "company_number": data.get("company_number"),
        "company_status": data.get("company_status"),
        "incorporation_date": data.get("date_of_creation"),
        "registered_office_address": addr,
        "sic_codes": sic_codes,
        "accounts_due_date": next_accounts.get("due_on"),
        "confirmation_statement_due_date": cs.get("next_due"),
        "accounts_overdue": accounts.get("overdue"),
        "confirmation_statement_overdue": cs.get("overdue"),
        "last_synced_at": _utc_iso(),
    }


def normalize_deadlines(profile: dict[str, Any]) -> dict[str, Any]:
    """Build deadlines payload from normalized profile fields."""
    acc = profile.get("accounts_due_date")
    cs = profile.get("confirmation_statement_due_date")
    upcoming: list[dict[str, Any]] = []
    if acc:
        upcoming.append(
            {
                "kind": "accounts",
                "due_date": acc,
                "label": "Annual accounts due at Companies House",
            }
        )
    if cs:
        upcoming.append(
            {
                "kind": "confirmation_statement",
                "due_date": cs,
                "label": "Confirmation statement due at Companies House",
            }
        )
    return {
        "accounts_due_date": acc,
        "confirmation_statement_due_date": cs,
        "overdue_flags": {
            "accounts_overdue": profile.get("accounts_overdue"),
            "confirmation_statement_overdue": profile.get("confirmation_statement_overdue"),
        },
        "upcoming_deadlines": upcoming,
        "source_label": "Companies House API (company profile)",
    }


def normalize_filing_history(data: dict[str, Any]) -> list[dict[str, Any]]:
    filings: list[dict[str, Any]] = []
    for item in data.get("items") or []:
        filings.append(
            {
                "date": item.get("date"),
                "type": item.get("type"),
                "description": item.get("description") or item.get("description_values"),
            }
        )
    return filings
