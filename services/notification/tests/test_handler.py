from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from notification.email import EmailMessage, EmailSender
from notification.handler import handle


class FakeEmailSender:
    """Fake implementing the EmailSender port — records calls without SES."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        if self._fail:
            raise RuntimeError("simulated email failure")
        self.sent.append(message)


async def test_attendance_recorded_sends_email() -> None:
    sender = FakeEmailSender()
    await handle(
        "AttendanceRecorded",
        {
            "attendance_id": "abc",
            "student_id": "ae5a8aa9-1234-1234-1234-000000000000",
            "course_id": "course-1",
            "status": "absent",
            "recorded_on": "2026-07-02",
        },
        sender,
    )

    assert len(sender.sent) == 1
    msg = sender.sent[0]
    assert "2026-07-02" in msg.subject
    assert "absent" in msg.body
    assert msg.to_address.startswith("parent-of-ae5a8aa9")


async def test_unknown_event_type_does_not_raise() -> None:
    sender = FakeEmailSender()
    # Unknown event types are silently logged and ignored — don't crash the consumer.
    await handle("SomeNewEvent", {"foo": "bar"}, sender)
    assert len(sender.sent) == 0


async def test_email_failure_propagates() -> None:
    sender = FakeEmailSender(fail=True)
    with pytest.raises(RuntimeError, match="simulated email failure"):
        await handle(
            "AttendanceRecorded",
            {"student_id": "abc", "course_id": "c", "status": "present", "recorded_on": "2026-07-02"},
            sender,
        )
