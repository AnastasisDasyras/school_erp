from redis.asyncio import Redis, from_url

from app.shared.config import get_settings


def make_redis() -> Redis:
    settings = get_settings()
    return from_url(settings.redis_url, decode_responses=True)


redis_client = make_redis()


def get_redis() -> Redis:
    """FastAPI dependency — one shared connection pool per process, like the DB engine."""
    return redis_client
