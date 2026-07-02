from __future__ import annotations

from app.shared.outbox.events import DomainEvent


class InMemoryOutboxWriter:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def add(self, event: DomainEvent) -> None:
        self.events.append(event)
