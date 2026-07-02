from __future__ import annotations

from typing import Protocol

from app.shared.outbox.events import DomainEvent


class OutboxWriter(Protocol):
    """Port: business services depend on this, never on SqlAlchemyOutboxRepository
    directly — keeps AttendanceService (and future Grades, etc.) unit-testable
    with an in-memory fake, the same dependency-inversion story as every
    other repository port in this project."""

    async def add(self, event: DomainEvent) -> None: ...
