"""Deterministic spend parsing for chat fast path."""

from app.services.spend_fast_parse import try_parse_spend_amount


def test_parse_gbp_pound_prefix() -> None:
    assert try_parse_spend_amount("Lunch £12.50") == (12.5, "GBP")


def test_parse_gbp_suffix() -> None:
    assert try_parse_spend_amount("12.50 GBP on fuel") == (12.5, "GBP")


def test_parse_usd() -> None:
    assert try_parse_spend_amount("Paid $40 for software") == (40.0, "USD")


def test_parse_eur() -> None:
    assert try_parse_spend_amount("€9.99 receipt") == (9.99, "EUR")


def test_reject_ambiguous_two_amounts() -> None:
    assert try_parse_spend_amount("£5 and £10") is None


def test_reject_no_currency() -> None:
    assert try_parse_spend_amount("spent 12.50 today") is None
