"""Structured latency instrumentation for POST /v1/chat."""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger("app.chat.pipeline")

chat_timing_var: contextvars.ContextVar["ChatTiming | None"] = contextvars.ContextVar(
    "chat_timing", default=None
)


def get_chat_timing() -> ChatTiming | None:
    return chat_timing_var.get()


@dataclass
class ChatTiming:
    """Per-request timings; logs structured events and one summary line."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    t0: float = field(default_factory=time.perf_counter)
    # stage name -> cumulative ms (non-overlapping spans unless noted)
    stages_ms: dict[str, float] = field(default_factory=dict)
    transaction_extraction_nested_ms: float = 0.0  # tool work inside LLM (subset of llm wall time)

    def _emit(self, event: str, **fields: object) -> None:
        payload = {"event": event, "request_id": self.request_id, **fields}
        logger.info("%s", json.dumps(payload, default=str))

    def event(self, name: str, **fields: object) -> None:
        self._emit(name, **fields)

    def span_start(self, stage: str) -> float:
        self._emit(f"{stage}_start")
        return time.perf_counter()

    def span_end(self, stage: str, start: float) -> float:
        ms = (time.perf_counter() - start) * 1000.0
        self.stages_ms[stage] = self.stages_ms.get(stage, 0.0) + ms
        self._emit(f"{stage}_end", ms=round(ms, 3))
        return ms

    def add_transaction_extraction_nested_ms(self, ms: float) -> None:
        """Bookkeeping tools inside Runner.run (overlaps llm wall time)."""
        self.transaction_extraction_nested_ms += ms

    def total_ms(self) -> float:
        return (time.perf_counter() - self.t0) * 1000.0

    def log_summary(self, *, fast_path: bool = False, extra: dict[str, object] | None = None) -> None:
        total = self.total_ms()
        breakdown = {
            k: round(v, 3) for k, v in sorted(self.stages_ms.items())
        }
        if self.transaction_extraction_nested_ms > 0:
            breakdown["transaction_extraction_nested_ms"] = round(
                self.transaction_extraction_nested_ms, 3
            )
        line = {
            "event": "chat_pipeline_summary",
            "request_id": self.request_id,
            "total_ms": round(total, 3),
            "fast_path": fast_path,
            "stages_ms": breakdown,
        }
        if extra:
            line["extra"] = extra
        logger.info("%s", json.dumps(line, default=str))


def set_chat_timing(timing: ChatTiming | None) -> contextvars.Token[ChatTiming | None]:
    return chat_timing_var.set(timing)
