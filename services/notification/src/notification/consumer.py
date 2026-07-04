from __future__ import annotations

import asyncio
import json

import boto3
import structlog
import tenacity
from opentelemetry import trace

from notification.config import Settings
from notification.email import EmailSender
from notification.handler import handle
from notification.tracing import tracer

log = structlog.get_logger("notification.consumer")


def _parse_body(raw_body: str) -> tuple[str, dict[str, str]]:
    """SNS wraps the original payload in an envelope when it delivers to SQS.
    We unwrap it to get event_type (from MessageAttributes) and the payload.

    SNS envelope shape:
    {
      "Type": "Notification",
      "Message": "<json string of the actual payload>",
      "MessageAttributes": {"event_type": {"Value": "AttendanceRecorded", ...}}
    }
    """
    envelope = json.loads(raw_body)
    event_type = envelope.get("MessageAttributes", {}).get("event_type", {}).get("Value", "")
    payload = json.loads(envelope.get("Message", "{}"))
    return event_type, payload


@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=30),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def _process_with_retry(
    event_type: str, payload: dict[str, str], email: EmailSender
) -> None:
    """Up to 3 attempts with exponential backoff before giving up.

    Giving up (reraise=True) means the SQS message is NOT deleted — it goes
    back into the queue and will be retried by SQS up to maxReceiveCount (3)
    times, after which SQS moves it to the DLQ automatically.

    So the full retry story is:
    - 3 in-process retries (tenacity, ~1+2+4s backoff)
    - if all 3 fail, SQS itself retries 3 more times (separate receive cycles)
    - if all those fail → DLQ
    """
    await handle(event_type, payload, email)


async def run_consumer(settings: Settings, email: EmailSender) -> None:
    """The SQS long-polling loop.

    WaitTimeSeconds=5: instead of constantly hammering the SQS API with empty
    polls, we tell SQS "wait up to 5s for a message before responding" — cuts
    API call volume by ~12x compared to short-polling, with no meaningful
    latency cost for this use case (5s extra delay on an email notification
    is fine).
    """
    sqs = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    queue_url = settings.sqs_notification_queue_url

    log.info("notification_consumer_started", queue_url=queue_url)

    while True:
        try:
            response = await asyncio.to_thread(
                sqs.receive_message,
                QueueUrl=queue_url,
                MaxNumberOfMessages=settings.sqs_max_messages,
                WaitTimeSeconds=settings.sqs_wait_seconds,
                MessageAttributeNames=["All"],
            )
        except Exception:
            log.exception("sqs_receive_failed")
            await asyncio.sleep(5)
            continue

        for msg in response.get("Messages", []):
            receipt = msg["ReceiptHandle"]
            event_type = "unknown"
            try:
                event_type, payload = _parse_body(msg["Body"])
                log.info("message_received", event_type=event_type)
                with tracer.start_as_current_span(
                    f"notification.process {event_type}",
                    attributes={"messaging.event_type": event_type},
                ):
                    await _process_with_retry(event_type, payload, email)
                await asyncio.to_thread(
                    sqs.delete_message, QueueUrl=queue_url, ReceiptHandle=receipt
                )
                log.info("message_deleted", event_type=event_type)
            except Exception:
                # Don't delete — let SQS retry and eventually route to DLQ.
                log.exception("message_processing_failed", event_type=event_type)
