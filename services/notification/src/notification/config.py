from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    log_level: str = "INFO"

    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = "http://localhost:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    sqs_notification_queue_url: str = (
        "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/notification-queue"
    )

    # SES — LocalStack emulates it; in real AWS this would be a verified sender address.
    ses_from_address: str = "noreply@school.local"

    # How many messages to receive in one SQS poll (max 10).
    sqs_max_messages: int = 10
    sqs_wait_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
