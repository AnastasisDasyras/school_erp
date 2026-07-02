from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.application.service import AttendanceService
from app.modules.attendance.infrastructure.repository import SqlAlchemyAttendanceRepository
from app.shared.database.session import get_session
from app.shared.idempotency.repository import SqlAlchemyIdempotencyStore
from app.shared.outbox.repository import SqlAlchemyOutboxRepository


def get_attendance_service(session: AsyncSession = Depends(get_session)) -> AttendanceService:
    """Wires the attendance repository and the outbox repository onto the
    *same* session, so the attendance insert and the outbox row are written
    in one transaction — see ADR 0008."""
    repository = SqlAlchemyAttendanceRepository(session)
    outbox = SqlAlchemyOutboxRepository(session)
    return AttendanceService(repository, outbox)


def get_idempotency_store(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyIdempotencyStore:
    return SqlAlchemyIdempotencyStore(session)
