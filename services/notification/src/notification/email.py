from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

import boto3
import pybreaker

from notification.config import Settings

# Circuit breaker wraps the SES call specifically — if the email provider
# is down, the breaker opens after 3 consecutive failures and short-circuits
# for 30s before retrying. This prevents the consumer from being stuck in a
# tight failure loop hammering a broken dependency.
_email_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


@dataclass(frozen=True)
class EmailMessage:
    to_address: str
    subject: str
    body: str


class EmailSender(Protocol):
    """Port: consumer depends on this, not SES directly — swappable for a
    fake in unit tests without any AWS calls."""

    async def send(self, message: EmailMessage) -> None: ...


class SesEmailSender:
    """Adapter: boto3 SES, wrapped in a circuit breaker.

    Using asyncio.to_thread since boto3 is sync-only — same pattern as the
    SNS publisher in the monolith's outbox relay.
    """

    def __init__(self, settings: Settings) -> None:
        self._from = settings.ses_from_address
        self._client = boto3.client(
            "ses",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    @_email_breaker
    def _send_sync(self, message: EmailMessage) -> None:
        self._client.send_email(
            Source=self._from,
            Destination={"ToAddresses": [message.to_address]},
            Message={
                "Subject": {"Data": message.subject},
                "Body": {"Text": {"Data": message.body}},
            },
        )

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)
