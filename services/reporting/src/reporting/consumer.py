from __future__ import annotations

import asyncio
import json

import boto3
import structlog
import tenacity

from reporting.config import Settings
from reporting.database import make_session_factory
from reporting.handler import SqlAlchemyAuditWriter, handle

log = structlog.get_logger("reporting.consumer")


def _parse_body(raw_body: str) -> tuple[str, dict[str, str]]:
    """Unwrap the SNS envelope — same structure as the Notification consumer."""
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
    event_type: str, payload: dict[str, str], settings: Settings
) -> None:
    session_factory = make_session_factory()
    async with session_factory() as session:
        writer = SqlAlchemyAuditWriter(session)
        await handle(event_type, payload, writer)


async def run_consumer(settings: Settings) -> None:
    sqs = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    queue_url = settings.sqs_reporting_queue_url

    log.info("reporting_consumer_started", queue_url=queue_url)

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
                await _process_with_retry(event_type, payload, settings)
                await asyncio.to_thread(
                    sqs.delete_message, QueueUrl=queue_url, ReceiptHandle=receipt
                )
                log.info("message_deleted", event_type=event_type)
            except Exception:
                log.exception("message_processing_failed", event_type=event_type)
