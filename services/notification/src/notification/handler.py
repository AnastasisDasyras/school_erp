from __future__ import annotations

import structlog

from notification.email import EmailMessage, EmailSender

log = structlog.get_logger("notification.handler")


async def handle(event_type: str, payload: dict[str, str], email: EmailSender) -> None:
    """Route an incoming event to the right notification logic.

    New event types are added here — the consumer loop (consumer.py) doesn't
    need to change, it just calls handle() with whatever arrives.
    """
    if event_type == "AttendanceRecorded":
        await _handle_attendance_recorded(payload, email)
    else:
        log.warning("unknown_event_type", event_type=event_type)


async def _handle_attendance_recorded(
    payload: dict[str, str], email: EmailSender
) -> None:
    student_id = payload.get("student_id", "unknown")
    course_id = payload.get("course_id", "unknown")
    status = payload.get("status", "unknown")
    recorded_on = payload.get("recorded_on", "unknown")

    # In a real system this would look up student/parent email from a DB.
    # Here we simulate that with a deterministic placeholder address so
    # LocalStack SES receives something concrete.
    to_address = f"parent-of-{student_id[:8]}@school.local"

    message = EmailMessage(
        to_address=to_address,
        subject=f"Attendance update for {recorded_on}",
        body=(
            f"Your student's attendance has been recorded.\n\n"
            f"Status: {status}\n"
            f"Course: {course_id}\n"
            f"Date: {recorded_on}\n"
        ),
    )

    await email.send(message)
    log.info(
        "notification_sent",
        event_type="AttendanceRecorded",
        student_id=student_id,
        status=status,
        to=to_address,
    )
