from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
    """Base shape for anything written to the outbox. `event_type` becomes
    the SNS message attribute consumers filter on; `payload` is whatever
    JSON-serializable dict the specific event needs."""

    event_type: str
    payload: dict[str, str]
