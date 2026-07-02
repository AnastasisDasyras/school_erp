from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.outbox.events import DomainEvent
from app.shared.outbox.orm import OutboxEventModel, OutboxStatus


class SqlAlchemyOutboxRepository:
    """Two distinct usage modes on the same table, by design:

    - `add()` is called from *business* services (e.g. AttendanceService),
      on the same session as the business write, and only ever flushes —
      never commits. The caller's router commits the business row and the
      outbox row together.
    - `list_pending()` / `mark_published()` / `mark_failed()` are called by
      the relay process (a separate worker, its own session/commits) which
      polls this table and never touches business tables at all.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: DomainEvent) -> None:
        self._session.add(
            OutboxEventModel(
                id=uuid.uuid4(),
                event_type=event.event_type,
                payload=json.dumps(event.payload),
                status=OutboxStatus.PENDING,
            )
        )
        await self._session.flush()

    async def list_pending(self, *, limit: int = 50) -> list[OutboxEventModel]:
        stmt = (
            select(OutboxEventModel)
            .where(OutboxEventModel.status == OutboxStatus.PENDING)
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_published(self, event_id: uuid.UUID) -> None:
        row = await self._session.get(OutboxEventModel, event_id)
        if row is not None:
            row.status = OutboxStatus.PUBLISHED
            row.published_at = datetime.now(UTC)

    async def mark_failed(self, event_id: uuid.UUID) -> None:
        row = await self._session.get(OutboxEventModel, event_id)
        if row is not None:
            row.attempts += 1
            row.status = OutboxStatus.FAILED
