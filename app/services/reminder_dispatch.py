"""
Future reminder delivery by channel (email / WhatsApp / Slack).

Internal testing uses `in_app` only; dispatch is intentionally a no-op for now.
When integrating, register callables per channel without changing ORM fields.
"""

from __future__ import annotations

from typing import Any, Callable

DispatchFn = Callable[..., None]

_REGISTRY: dict[str, DispatchFn] = {
    "in_app": lambda **kwargs: None,
    "email": lambda **kwargs: None,
    "whatsapp": lambda **kwargs: None,
    "slack": lambda **kwargs: None,
}


def register_channel_dispatcher(channel: str, fn: DispatchFn) -> None:
    _REGISTRY[channel] = fn


def dispatch_reminder_stub(channel: str, payload: dict[str, Any]) -> None:
    """Placeholder invoked after DB save; replace with real queues/webhooks later."""
    fn = _REGISTRY.get(channel)
    if fn:
        fn(**payload)
