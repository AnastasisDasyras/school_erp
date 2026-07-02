import uuid

import pytest

from app.modules.attendance.application.dto import RecordAttendanceInput
from app.modules.attendance.application.exceptions import AttendanceAlreadyRecordedError
from app.modules.attendance.application.service import ATTENDANCE_RECORDED_EVENT, AttendanceService
from app.modules.attendance.domain.attendance import AttendanceStatus
from tests.unit.attendance_fakes import InMemoryAttendanceRepository
from tests.unit.outbox_fakes import InMemoryOutboxWriter


@pytest.fixture
def outbox() -> InMemoryOutboxWriter:
    return InMemoryOutboxWriter()


@pytest.fixture
def service(outbox: InMemoryOutboxWriter) -> AttendanceService:
    return AttendanceService(InMemoryAttendanceRepository(), outbox)


async def test_record_writes_an_outbox_event(
    service: AttendanceService, outbox: InMemoryOutboxWriter
) -> None:
    student_id, course_id = uuid.uuid4(), uuid.uuid4()

    await service.record(
        RecordAttendanceInput(
            student_id=student_id, course_id=course_id, status=AttendanceStatus.PRESENT
        )
    )

    assert len(outbox.events) == 1
    event = outbox.events[0]
    assert event.event_type == ATTENDANCE_RECORDED_EVENT
    assert event.payload["student_id"] == str(student_id)
    assert event.payload["course_id"] == str(course_id)
    assert event.payload["status"] == "present"


async def test_record_rejects_duplicate_same_day(
    service: AttendanceService, outbox: InMemoryOutboxWriter
) -> None:
    student_id, course_id = uuid.uuid4(), uuid.uuid4()
    data = RecordAttendanceInput(
        student_id=student_id, course_id=course_id, status=AttendanceStatus.PRESENT
    )

    await service.record(data)
    with pytest.raises(AttendanceAlreadyRecordedError):
        await service.record(data)

    # The critical assertion for the outbox story: a rejected second record()
    # must not have written a second outbox event — exactly the "no event
    # without a successful business write" guarantee ADR 0008 is about.
    assert len(outbox.events) == 1
