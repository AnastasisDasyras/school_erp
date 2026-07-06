from __future__ import annotations

import json

import pytest

from notification import lambda_handler
from notification.email import EmailMessage


class FakeEmailSender:
    """Fake implementing the EmailSender port — records calls without SES.

    Same pattern as tests/test_handler.py; duplicated here so the Lambda test
    is self-contained.
    """

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        if self._fail:
            raise RuntimeError("simulated email failure")
        self.sent.append(message)


def _sns_envelope(event_type: str, payload: dict[str, str]) -> str:
    """Build the SNS-over-SQS envelope string that lands in Records[].body.

    Mirrors the shape _parse_body expects: MessageAttributes carries the
    event_type, and Message is the *double-JSON-encoded* payload.
    """
    return json.dumps(
        {
            "Type": "Notification",
            "Message": json.dumps(payload),
            "MessageAttributes": {"event_type": {"Type": "String", "Value": event_type}},
        }
    )


def _sqs_event(*bodies: str) -> dict:
    """Wrap SNS envelope bodies in the SQS event shape AWS passes to a Lambda."""
    return {"Records": [{"body": body} for body in bodies]}


@pytest.fixture
def fake_email(monkeypatch: pytest.MonkeyPatch) -> FakeEmailSender:
    """Swap the module-level SES sender for a fake for the duration of a test."""
    sender = FakeEmailSender()
    monkeypatch.setattr(lambda_handler, "_email", sender)
    return sender


def test_attendance_recorded_sends_email(fake_email: FakeEmailSender) -> None:
    event = _sqs_event(
        _sns_envelope(
            "AttendanceRecorded",
            {
                "student_id": "ae5a8aa9-1234-1234-1234-000000000000",
                "course_id": "course-1",
                "status": "absent",
                "recorded_on": "2026-07-02",
            },
        )
    )

    lambda_handler.handler(event, None)

    assert len(fake_email.sent) == 1
    msg = fake_email.sent[0]
    assert "2026-07-02" in msg.subject
    assert "absent" in msg.body
    assert msg.to_address.startswith("parent-of-ae5a8aa9")


def test_batch_of_multiple_records(fake_email: FakeEmailSender) -> None:
    event = _sqs_event(
        _sns_envelope(
            "AttendanceRecorded",
            {"student_id": "s1", "course_id": "c", "status": "present", "recorded_on": "2026-07-02"},  # noqa: E501
        ),
        _sns_envelope(
            "AttendanceRecorded",
            {"student_id": "s2", "course_id": "c", "status": "absent", "recorded_on": "2026-07-02"},  # noqa: E501
        ),
    )

    lambda_handler.handler(event, None)

    assert len(fake_email.sent) == 2


def test_unknown_event_type_is_noop(fake_email: FakeEmailSender) -> None:
    event = _sqs_event(_sns_envelope("SomeNewEvent", {"foo": "bar"}))

    lambda_handler.handler(event, None)

    assert len(fake_email.sent) == 0


def test_empty_records_is_noop(fake_email: FakeEmailSender) -> None:
    lambda_handler.handler({"Records": []}, None)
    assert len(fake_email.sent) == 0
