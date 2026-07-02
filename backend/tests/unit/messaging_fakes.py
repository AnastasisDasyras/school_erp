from __future__ import annotations


class InMemoryMessagePublisher:
    """Fake for the MessagePublisher port — records publishes instead of
    calling boto3/SNS. Lets relay logic be unit-tested without LocalStack."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.published: list[tuple[str, str]] = []

    async def publish(self, *, event_type: str, payload: str) -> None:
        if self._fail:
            raise RuntimeError("simulated publish failure")
        self.published.append((event_type, payload))
