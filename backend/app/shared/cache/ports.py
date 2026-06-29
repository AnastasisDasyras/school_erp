from __future__ import annotations

from typing import Protocol


class Cache(Protocol):
    """Port: services depend on this, never on redis.asyncio directly.

    Kept deliberately tiny (get/set/delete-by-prefix) — just enough for the
    cache-aside pattern. A fake in tests means cache logic is unit-testable
    without a real Redis.
    """

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...
