from __future__ import annotations

import asyncio

import boto3

from app.shared.config.settings import Settings


class SnsPublisher:
    """Adapter implementing MessagePublisher using boto3 SNS.

    boto3 is sync-only; `asyncio.to_thread` runs each publish call off the
    event loop rather than blocking it — acceptable here because the relay
    is the only caller and it's not on the request/response hot path.
    """

    def __init__(self, settings: Settings) -> None:
        self._topic_arn = settings.sns_events_topic_arn
        self._client = boto3.client(
            "sns",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    async def publish(self, *, event_type: str, payload: str) -> None:
        await asyncio.to_thread(
            self._client.publish,
            TopicArn=self._topic_arn,
            Message=payload,
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event_type},
            },
        )
