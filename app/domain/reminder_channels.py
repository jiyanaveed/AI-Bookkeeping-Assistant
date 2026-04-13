"""Reminder delivery channels — integration stubs planned for email/whatsapp/slack."""

from __future__ import annotations

# Values stored in DB; dispatch layer can map each to providers later.
REMINDER_CHANNELS: tuple[str, ...] = ("in_app", "email", "whatsapp", "slack")


class InvalidChannelError(ValueError):
    pass


def normalize_reminder_channel(value: str) -> str:
    c = (value or "").strip().lower()
    if c not in REMINDER_CHANNELS:
        raise InvalidChannelError(
            f"channel must be one of: {', '.join(REMINDER_CHANNELS)}; got {value!r}"
        )
    return c
