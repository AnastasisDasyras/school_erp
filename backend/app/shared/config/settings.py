from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """12-factor config: every value comes from the environment, with sane local defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "school-erp"
    environment: str = "local"
    log_level: str = "INFO"
    log_dir: str = "app/logs"

    database_url: str = "postgresql+asyncpg://erp:erp@localhost:5432/erp"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # AWS / LocalStack — same client code, different endpoint per environment.
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = "http://localhost:4566"  # None in real AWS
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    # Account id is always "000000000000" under LocalStack; in real AWS this
    # whole ARN would come from Terraform output / env injection instead.
    sns_events_topic_arn: str = "arn:aws:sns:us-east-1:000000000000:school-erp-events"

    otel_exporter_otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
