"""Deterministic parse of a single obvious amount + currency from a user message (spending fast path)."""

from __future__ import annotations

import re
from typing import Pattern


def _normalize_amount(raw: str) -> float | None:
    s = raw.strip()
    if not s:
        return None
    # UK/US: 12.50 or 12,50 (European decimals)
    if s.count(",") == 1 and s.count(".") == 0:
        parts = s.split(",")
        if len(parts[1]) <= 2 and parts[1].isdigit():
            s = parts[0] + "." + parts[1]
    elif "," in s and "." in s:
        # e.g. 1,234.56 → remove thousands comma
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0 or v > 1e12:
        return None
    return v


def _collect_matches(pattern: Pattern[str], text: str, currency: str) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    for m in pattern.finditer(text):
        amt = _normalize_amount(m.group(1))
        if amt is not None:
            out.append((amt, currency))
    return out


def try_parse_spend_amount(text: str) -> tuple[float, str] | None:
    """
    If the message contains exactly one clear monetary amount with an explicit currency
    (symbol or ISO code), return (amount, currency). Otherwise None (fall back to LLM).
    """
    t = (text or "").strip()
    if not t:
        return None

    patterns: list[tuple[Pattern[str], str]] = [
        (re.compile(r"£\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "GBP"),
        (re.compile(r"(\d[\d,]*(?:[.,]\d{1,2})?)\s*£"), "GBP"),
        (re.compile(r"(?i)(\d[\d,]*(?:[.,]\d{1,2})?)\s*GBP\b"), "GBP"),
        (re.compile(r"(?i)GBP\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "GBP"),
        (re.compile(r"\$\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "USD"),
        (re.compile(r"(\d[\d,]*(?:[.,]\d{1,2})?)\s*\$"), "USD"),
        (re.compile(r"(?i)(\d[\d,]*(?:[.,]\d{1,2})?)\s*USD\b"), "USD"),
        (re.compile(r"(?i)USD\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "USD"),
        (re.compile(r"€\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "EUR"),
        (re.compile(r"(\d[\d,]*(?:[.,]\d{1,2})?)\s*€"), "EUR"),
        (re.compile(r"(?i)(\d[\d,]*(?:[.,]\d{1,2})?)\s*EUR\b"), "EUR"),
        (re.compile(r"(?i)EUR\s*(\d[\d,]*(?:[.,]\d{1,2})?)"), "EUR"),
    ]

    found: list[tuple[float, str]] = []
    for pat, cur in patterns:
        found.extend(_collect_matches(pat, t, cur))

    if not found:
        return None

    # De-dupe identical (amount, currency) from overlapping regex hits
    uniq: list[tuple[float, str]] = []
    for pair in found:
        if pair not in uniq:
            uniq.append(pair)

    if len(uniq) != 1:
        return None

    return uniq[0]
