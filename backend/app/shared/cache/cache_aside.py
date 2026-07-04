from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.shared.cache.ports import Cache
from app.shared.observability.metrics import cache_hits_total, cache_misses_total


async def cached[T](
    cache: Cache,
    key: str,
    *,
    ttl_seconds: int,
    loader: Callable[[], Awaitable[T]],
    to_json: Callable[[T], str],
    from_json: Callable[[str], T],
) -> T:
    """Cache-aside: check cache, fall through to `loader` on a miss, write-through.

    The conversion functions exist because cache values are JSON strings (a
    redis-asyncio detail), but services should work with their own dataclasses
    (StudentPage, etc.) — keeping serialization out of the application layer.
    """
    prefix = key.split(":")[0]
    raw = await cache.get(key)
    if raw is not None:
        cache_hits_total.labels(key_prefix=prefix).inc()
        return from_json(raw)

    cache_misses_total.labels(key_prefix=prefix).inc()
    value = await loader()
    await cache.set(key, to_json(value), ttl_seconds=ttl_seconds)
    return value
