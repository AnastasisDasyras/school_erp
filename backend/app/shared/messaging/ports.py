from __future__ import annotations

from typing import Protocol


class MessagePublisher(Protocol):
    """Port: the relay depends on this, never on boto3 directly. Swapping
    LocalStack for real AWS SNS is a config change (endpoint_url), not a
    code change — this Protocol is what makes that true: nothing above this
    layer knows boto3 exists."""

    async def publish(self, *, event_type: str, payload: str) -> None: ...
