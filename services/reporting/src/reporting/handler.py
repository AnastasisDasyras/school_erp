from __future__ import annotations

import json
import uuid
from typing import Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from reporting.models import AuditLogEntry

log = structlog.get_logger("reporting.handler")


class AuditWriter(Protocol):
    """Port: the handler depends on this, not SQLAlchemy directly — lets unit
    tests inject an in-memory fake without a real DB."""

    async def write(self, *, event_type: str, payload: str) -> None: ...


class SqlAlchemyAuditWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(self, *, event_type: str, payload: str) -> None:
        self._session.add(
            AuditLogEntry(id=uuid.uuid4(), event_type=event_type, payload=payload)
        )
        await self._session.commit()


async def handle(event_type: str, payload: dict[str, str], writer: AuditWriter) -> None:
    """All event types get logged to the audit trail — Reporting is a
    general-purpose read-model builder, not event-specific like Notification."""
    raw_payload = json.dumps(payload)
    await writer.write(event_type=event_type, payload=raw_payload)
    log.info("audit_log_written", event_type=event_type)
