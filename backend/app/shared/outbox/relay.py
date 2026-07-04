from __future__ import annotations

import asyncio
import logging

import structlog

from app.shared.config.settings import get_settings
from app.shared.database.session import SessionFactory
from app.shared.messaging.ports import MessagePublisher
from app.shared.messaging.sns_publisher import SnsPublisher
from app.shared.observability.metrics import (
    outbox_failed_total,
    outbox_pending_events,
    outbox_published_total,
)
from app.shared.outbox.repository import SqlAlchemyOutboxRepository

log = structlog.get_logger("outbox_relay")

_POLL_INTERVAL_SECONDS = 120.0


async def relay_once(publisher: MessagePublisher) -> int:
    """One poll cycle: claim a batch of PENDING rows, publish each, mark
    published/failed, commit. `with_for_update(skip_locked=True)` in
    `list_pending` means if a second relay instance ever ran concurrently,
    each would claim disjoint rows instead of double-publishing — the same
    `SELECT ... FOR UPDATE` idea as the course-seat locking in ADR 0004,
    applied here so the relay can later be scaled out without re-architecting.
    """
    published = 0
    async with SessionFactory() as session:
        repository = SqlAlchemyOutboxRepository(session)
        pending = await repository.list_pending()

        outbox_pending_events.set(len(pending))
        for row in pending:
            try:
                await publisher.publish(event_type=row.event_type, payload=row.payload)
            except Exception:
                log.exception(
                    "outbox_publish_failed", event_id=str(row.id), event_type=row.event_type
                )
                await repository.mark_failed(row.id)
                outbox_failed_total.inc()
                continue
            await repository.mark_published(row.id)
            outbox_published_total.inc()
            published += 1
            log.info("outbox_published", event_id=str(row.id), event_type=row.event_type)

        await session.commit()
    return published


async def run_relay_forever() -> None:
    """Entry point for the standalone relay process (its own container,
    not part of the FastAPI app) — polling, not push, because the outbox
    table has no native "notify me on insert" mechanism without LISTEN/NOTIFY,
    which is an optimization left for later, not a correctness requirement.
    """
    settings = get_settings()
    logging.basicConfig(format="%(message)s", level=settings.log_level)
    publisher = SnsPublisher(settings)

    log.info("outbox_relay_started", poll_interval_seconds=_POLL_INTERVAL_SECONDS)
    while True:
        try:
            count = await relay_once(publisher)
            if count:
                log.info("outbox_relay_cycle", published_count=count)
        except Exception:
            log.exception("outbox_relay_cycle_failed")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_relay_forever())
