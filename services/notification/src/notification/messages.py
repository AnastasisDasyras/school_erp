from __future__ import annotations

import json


def parse_sns_body(raw_body: str) -> tuple[str, dict[str, str]]:
    """Unwrap the SNS-over-SQS envelope into (event_type, payload).

    SNS wraps the original payload in an envelope when it delivers to an SQS
    subscriber. Both the container consumer and the Lambda receive this same
    envelope string (as the SQS message body), so this parsing lives here —
    a dependency-free module both entry points can import without dragging in
    boto3 / OpenTelemetry / the poll loop.

    SNS envelope shape:
    {
      "Type": "Notification",
      "Message": "<json string of the actual payload>",
      "MessageAttributes": {"event_type": {"Value": "AttendanceRecorded", ...}}
    }

    Note `Message` is double-JSON-encoded — it's a JSON string that must be
    decoded a second time to get the payload dict.
    """
    envelope = json.loads(raw_body)
    event_type = envelope.get("MessageAttributes", {}).get("event_type", {}).get("Value", "")
    payload = json.loads(envelope.get("Message", "{}"))
    return event_type, payload
