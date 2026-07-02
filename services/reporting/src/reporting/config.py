from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    log_level: str = "INFO"

    # Own database connection — same Postgres instance as the monolith in
    # local dev, but logically separate: this service only touches its own
    # tables and never queries the monolith's tables directly.
    database_url: str = "postgresql+asyncpg://erp:erp@localhost:5432/erp"

    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = "http://localhost:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    sqs_reporting_queue_url: str = (
        "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/reporting-queue"
    )

    sqs_max_messages: int = 10
    sqs_wait_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
