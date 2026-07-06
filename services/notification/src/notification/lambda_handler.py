"""AWS Lambda entry point for the notification service.

This is a *second* delivery path for the exact same email logic that the
container consumer (`consumer.py` / `main.py`) runs. It exists to contrast the
two runtime models:

  Container consumer (consumer.run_consumer)      AWS Lambda (this file)
  ----------------------------------------        ----------------------------
  A process that runs `while True:` forever,       AWS invokes handler() only
  long-polling SQS with receive_message.           when messages arrive.
  *Our* code owns the poll loop.                   *AWS* owns the poll loop
                                                    (the SQS event-source mapping
                                                    polls and batches for us).
  On success we call sqs.delete_message.           AWS auto-deletes the batch
                                                    when the invocation returns
                                                    without raising.
  On failure we DON'T delete → SQS redelivers →    On an exception AWS reports
  after maxReceiveCount → DLQ.                      the batch as failed → SQS
                                                    redelivers → DLQ. Same story,
                                                    AWS drives it.
  Pay for the container 24/7.                       Pay per invocation (ms); $0
                                                    while idle.

The business logic — `handle()`, `_parse_body()`, `SesEmailSender` — is reused
unchanged. This module is a thin adapter: turn AWS's `event` shape into the
`(event_type, payload)` our handler already understands.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

# Reused business logic. parse_sns_body lives in its own dependency-free module
# so importing it here does NOT pull in consumer.py's boto3 / OpenTelemetry /
# poll-loop machinery — keeping the Lambda's import graph (and cold start) lean.
from notification.config import get_settings
from notification.email import SesEmailSender
from notification.handler import handle
from notification.messages import parse_sns_body

log = structlog.get_logger("notification.lambda")

# ── Module scope: runs ONCE per cold start, reused across warm invocations ──
# Building the boto3 SES client (and reading settings) here — rather than inside
# handler() — means a warm Lambda container skips this on subsequent calls.
# Bonus: the module-level pybreaker breaker in email.py persists across warm
# invocations too, so consecutive SES failures still open the circuit.
#
# NOTE for real AWS (vs this LocalStack demo): the config defaults point at
# LocalStack with test/test creds. In production you would leave
# AWS_ENDPOINT_URL unset (so boto3 hits real SES) and let the Lambda execution
# role supply credentials via boto3's default provider chain, rather than the
# hardcoded "test" keys.
_settings = get_settings()
_email = SesEmailSender(_settings)


def handler(event: dict[str, Any], context: Any) -> None:
    """Lambda entry point. Invoked by the SQS event-source mapping.

    `event["Records"]` is the batch of SQS messages AWS polled for us. Each
    record's `body` is the SNS envelope string (SNS -> SQS fan-out), which is
    exactly what `_parse_body` expects — it unwraps the envelope and
    double-decodes the inner `Message`.

    Failure model (kept intentionally simple for the demo): if any record
    raises, we let it propagate. Lambda then marks the whole batch as failed,
    SQS redelivers, and after maxReceiveCount the message lands in the DLQ —
    mirroring the container consumer's behavior.

    (Production refinement, out of scope here: return
    {"batchItemFailures": [...]} to fail only the offending messages instead of
    the whole batch — SQS partial batch response.)
    """
    records = event.get("Records", [])
    log.info("lambda_invoked", record_count=len(records))

    for record in records:
        event_type, payload = parse_sns_body(record["body"])
        log.info("message_received", event_type=event_type)
        # handle() and SesEmailSender.send() are async; drive them with
        # asyncio.run since the Lambda entry point is a plain sync function.
        asyncio.run(handle(event_type, payload, _email))
        log.info("message_processed", event_type=event_type)
