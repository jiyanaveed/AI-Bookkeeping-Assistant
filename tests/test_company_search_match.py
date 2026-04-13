"""Unit tests for conservative company search classification."""

from app.services.company_search_match import (
    classify_company_search_results,
    pick_dominant_strong_matches,
)


def test_fake_name_no_strong_only_loose() -> None:
    items = [
        {"title": "ABC WIDGETS LIMITED", "company_number": "111", "company_status": "active"},
        {"title": "XYZ GROUP PLC", "company_number": "222", "company_status": "active"},
    ]
    out = classify_company_search_results("Random Fake 123 Company Ltd", items)
    assert out["has_strong_match"] is False
    assert out["match_assessment"] == "no_strong_match_loose_only"
    assert out["strong_matches"] == []
    assert len(out["loosely_related_candidates"]) <= 8
    assert "loosely" in out["response_framing"].lower() or "weak" in out["response_framing"].lower()


def test_tesco_strong_match() -> None:
    items = [
        {"title": "TESCO PLC", "company_number": "00445790", "company_status": "active"},
    ]
    out = classify_company_search_results("Tesco PLC", items)
    assert out["has_strong_match"] is True
    assert len(out["strong_matches"]) >= 1
    assert out["strong_matches"][0]["company_number"] == "00445790"
    assert out["loosely_related_candidates"] == []


def test_no_results() -> None:
    out = classify_company_search_results("Unknownquery Zzz", [])
    assert out["has_strong_match"] is False
    assert out["match_assessment"] == "no_results"


def test_pick_dominant_single_perfect_score_among_many_strong() -> None:
    strong = [
        {"company_name": "TESCO PLC", "company_number": "00445790", "match_score": 1.0},
        {"company_name": "TESCO STORES LIMITED", "company_number": "02222222", "match_score": 0.88},
        {"company_name": "OTHER CO", "company_number": "03333333", "match_score": 0.86},
    ]
    picked = pick_dominant_strong_matches("Tesco PLC", strong)
    assert len(picked) == 1
    assert picked[0]["company_number"] == "00445790"


def test_pick_dominant_keeps_ambiguous_when_two_close() -> None:
    strong = [
        {"company_name": "ACME HOLDINGS LTD", "company_number": "111", "match_score": 0.92},
        {"company_name": "ACME RETAIL LTD", "company_number": "222", "match_score": 0.91},
    ]
    picked = pick_dominant_strong_matches("Acme Ltd", strong)
    assert len(picked) == 2
