from __future__ import annotations

import pytest

from reporting.handler import AuditWriter, handle


class FakeAuditWriter:
    """Fake implementing the AuditWriter port — stores entries in memory."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    async def write(self, *, event_type: str, payload: str) -> None:
        self.entries.append((event_type, payload))


async def test_any_event_type_gets_logged() -> None:
    writer = FakeAuditWriter()
    await handle("AttendanceRecorded", {"student_id": "s1", "status": "present"}, writer)

    assert len(writer.entries) == 1
    event_type, payload = writer.entries[0]
    assert event_type == "AttendanceRecorded"
    assert "s1" in payload


async def test_multiple_events_all_logged() -> None:
    writer = FakeAuditWriter()
    await handle("AttendanceRecorded", {"x": "1"}, writer)
    await handle("GradeSubmitted", {"x": "2"}, writer)

    assert len(writer.entries) == 2
    assert writer.entries[0][0] == "AttendanceRecorded"
    assert writer.entries[1][0] == "GradeSubmitted"
