from __future__ import annotations

from app.modules.attendance.application.dto import AttendanceView, RecordAttendanceInput
from app.modules.attendance.application.exceptions import AttendanceAlreadyRecordedError
from app.modules.attendance.application.ports import AttendanceRepository
from app.modules.attendance.domain.attendance import AttendanceRecord
from app.shared.outbox.events import DomainEvent
from app.shared.outbox.ports import OutboxWriter

ATTENDANCE_RECORDED_EVENT = "AttendanceRecorded"


def _to_view(record: AttendanceRecord) -> AttendanceView:
    return AttendanceView(
        id=record.id,
        student_id=record.student_id,
        course_id=record.course_id,
        status=record.status,
        recorded_on=record.recorded_on,
    )


class AttendanceService:
    """The outbox pattern demo for this project (ADR 0008).

    `record()` writes the attendance row *and* an `AttendanceRecorded` outbox
    row through the same `outbox` repository, which shares this service's
    session — both flush here, and the caller (the router) commits once.
    Neither write is visible to anything outside this transaction until that
    commit happens, so a crash between "insert attendance" and "insert
    outbox row" is impossible: they're the same atomic operation as far as
    Postgres is concerned. A separate relay process (shared/outbox/relay.py)
    is the only thing that ever reads PENDING outbox rows and publishes them
    to SNS — this service never talks to SNS/boto3 directly.
    """

    def __init__(
        self,
        repository: AttendanceRepository,
        outbox: OutboxWriter,
    ) -> None:
        self._repository = repository
        self._outbox = outbox

    async def record(self, data: RecordAttendanceInput) -> AttendanceView:
        record = AttendanceRecord.create(
            student_id=data.student_id, course_id=data.course_id, status=data.status
        )

        if await self._repository.exists_for_day(
            student_id=record.student_id,
            course_id=record.course_id,
            recorded_on=record.recorded_on,
        ):
            raise AttendanceAlreadyRecordedError(record.student_id, record.course_id)

        await self._repository.add(record)
        await self._outbox.add(
            DomainEvent(
                event_type=ATTENDANCE_RECORDED_EVENT,
                payload={
                    "attendance_id": str(record.id),
                    "student_id": str(record.student_id),
                    "course_id": str(record.course_id),
                    "status": record.status.value,
                    "recorded_on": record.recorded_on.isoformat(),
                },
            )
        )

        return _to_view(record)
