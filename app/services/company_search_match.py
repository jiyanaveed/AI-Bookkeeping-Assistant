"""Conservative classification of Companies House name search results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# Tokens that are too generic to support a "strong" match on overlap alone.
_GENERIC_TOKENS = frozenset(
    {
        "ltd",
        "limited",
        "plc",
        "llp",
        "uk",
        "company",
        "co",
        "the",
        "and",
        "group",
        "holdings",
        "holding",
        "international",
        "services",
        "service",
        "management",
        "investments",
        "enterprise",
        "enterprises",
        "trading",
        "solutions",
        "global",
    }
)

_MAX_STRONG = 10
_MAX_WEAK_DISPLAY = 8
_CH_RAW_LIMIT = 40  # fetch more from CH, then score and trim

_SUFFIX_PATTERN = re.compile(
    r"\b(ltd|limited|plc|llp|cic|community\s+interest\s+company)\b\.?",
    re.IGNORECASE,
)


def normalize_company_name(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _SUFFIX_PATTERN.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def significant_tokens(normalized: str) -> list[str]:
    return [t for t in normalized.split() if len(t) > 1 and t not in _GENERIC_TOKENS]


def _word_boundary_match(title_norm: str, token: str) -> bool:
    return bool(re.search(rf"(^| ){re.escape(token)}( |$)", title_norm))


@dataclass(frozen=True)
class ScoredItem:
    company_name: str | None
    company_number: str | None
    company_status: str | None
    tier: str  # "strong" | "weak"
    score: float


def _score_match(query_norm: str, title_norm: str) -> tuple[str, float]:
    """Return (tier, score) with tier strong or weak."""
    if not query_norm or not title_norm:
        return "weak", 0.0

    ratio = SequenceMatcher(None, query_norm, title_norm).ratio()

    if query_norm == title_norm:
        return "strong", 1.0

    if ratio >= 0.92:
        return "strong", ratio

    if len(query_norm) >= 10 and (title_norm.startswith(query_norm) or title_norm.endswith(query_norm)):
        return "strong", max(ratio, 0.91)

    sig_q = significant_tokens(query_norm)
    if sig_q:
        hits = sum(1 for t in sig_q if _word_boundary_match(title_norm, t))
        frac = hits / len(sig_q)
        if hits == len(sig_q) and len(sig_q) >= 2:
            return "strong", max(ratio, 0.88)
        if len(sig_q) == 1 and frac == 1.0 and len(query_norm) <= 40:
            return "strong", max(ratio, 0.85)
        if len(sig_q) >= 3 and frac >= 0.85:
            return "strong", max(ratio, 0.82)

    if ratio >= 0.82 and len(query_norm) >= 6:
        return "strong", ratio

    return "weak", ratio


def classify_company_search_results(query: str, items: list[dict]) -> dict:
    """
    Build tool output: strong vs weak matches, conservative framing, capped lists.
    `items` are raw Companies House `search/companies` elements (use `title` as name).
    """
    query_norm = normalize_company_name(query)
    scored: list[ScoredItem] = []

    for it in items[:_CH_RAW_LIMIT]:
        title = it.get("title") or ""
        title_norm = normalize_company_name(title)
        tier, score = _score_match(query_norm, title_norm)
        scored.append(
            ScoredItem(
                company_name=it.get("title"),
                company_number=it.get("company_number"),
                company_status=it.get("company_status"),
                tier=tier,
                score=round(score, 4),
            )
        )

    strong_ranked = sorted([x for x in scored if x.tier == "strong"], key=lambda x: -x.score)[
        :_MAX_STRONG
    ]
    weak_ranked = sorted([x for x in scored if x.tier == "weak"], key=lambda x: -x.score)[
        :_MAX_WEAK_DISPLAY
    ]

    has_strong = len(strong_ranked) > 0

    strong_payload = [
        {
            "company_name": s.company_name,
            "company_number": s.company_number,
            "company_status": s.company_status,
            "match_quality": "strong",
            "match_score": s.score,
        }
        for s in strong_ranked
    ]
    weak_payload = [
        {
            "company_name": s.company_name,
            "company_number": s.company_number,
            "company_status": s.company_status,
            "match_quality": "weak",
            "match_score": s.score,
        }
        for s in weak_ranked
    ]

    if has_strong:
        framing = (
            "Verified search results include at least one strong name match against the "
            "user query. You may proceed with those company numbers, still using tools for profiles and deadlines."
        )
        match_assessment = "strong_match_present"
    elif weak_payload:
        framing = (
            "I could not find a strong verified match for that company name. Companies House "
            "returned some loosely related names only—these are weak matches and must not be "
            "presented as if the requested company was found. Offer at most this short list if "
            "the user wants to pick a company number manually."
        )
        match_assessment = "no_strong_match_loose_only"
    else:
        framing = "No Companies House search hits were returned for this query."
        match_assessment = "no_results"
        weak_payload = []

    return {
        "query": query,
        "match_assessment": match_assessment,
        "has_strong_match": has_strong,
        "strong_matches": strong_payload,
        "loosely_related_candidates": [] if has_strong else weak_payload,
        "response_framing": framing,
    }


def pick_dominant_strong_matches(query: str, strong_matches: list[dict]) -> list[dict]:
    """
    Companies House search can yield many \"strong\" tier rows (e.g. same distinctive token).
    If one row is an exact normalized name match or sole match_score 1.0, or clearly ahead of #2, treat as a single selection.
    """
    if len(strong_matches) <= 1:
        return strong_matches
    query_norm = normalize_company_name(query)
    by_perfect = [s for s in strong_matches if float(s.get("match_score") or 0) >= 1.0 - 1e-9]
    if len(by_perfect) == 1:
        return by_perfect
    name_eq = [
        s
        for s in strong_matches
        if normalize_company_name(s.get("company_name") or "") == query_norm
    ]
    if len(name_eq) == 1:
        return name_eq
    ranked = sorted(strong_matches, key=lambda s: float(s.get("match_score") or 0), reverse=True)
    best, second = ranked[0], ranked[1] if len(ranked) > 1 else None
    b = float(best.get("match_score") or 0)
    s2 = float(second.get("match_score") or 0) if second else -1.0
    if b >= 0.99 and (second is None or (b - s2) >= 0.05):
        return [best]
    return strong_matches
