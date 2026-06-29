from __future__ import annotations

from redis.asyncio import Redis


class RedisCache:
    """Adapter implementing the Cache port using redis.asyncio."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)

    async def delete_prefix(self, prefix: str) -> None:
        # SCAN (not KEYS) so invalidating a prefix never blocks Redis on a
        # large keyspace — relevant once multiple modules share one Redis.
        async for key in self._redis.scan_iter(match=f"{prefix}*"):
            await self._redis.delete(key)
