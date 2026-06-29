from __future__ import annotations


class InMemoryCache:
    """Fake for the Cache port — no Redis, just a dict. Tracks hit/miss/set
    counts so tests can assert cache-aside behavior, not just final values."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self._store.get(key)

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        self.set_calls += 1
        self._store[key] = value

    async def delete_prefix(self, prefix: str) -> None:
        for key in [k for k in self._store if k.startswith(prefix)]:
            del self._store[key]
