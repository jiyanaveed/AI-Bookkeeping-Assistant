"""Unit tests for compliance deadline schedule helpers."""

from datetime import date

from app.services.compliance_deadline_sync import compute_trigger_date, offset_label


def test_offset_label() -> None:
    assert offset_label(0) == "due_date"
    assert offset_label(30) == "30_days_before"


def test_compute_trigger_date() -> None:
    due = date(2026, 6, 30)
    assert compute_trigger_date(due, 30) == date(2026, 5, 31)
    assert compute_trigger_date(due, 0) == due
