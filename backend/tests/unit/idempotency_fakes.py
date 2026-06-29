from __future__ import annotations

import uuid

from app.shared.idempotency.ports import StoredResponse


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], StoredResponse] = {}
        self.save_calls = 0

    async def get(self, *, key: str, endpoint: str) -> StoredResponse | None:
        return self._store.get((key, endpoint))

    async def save(
        self, *, key: str, endpoint: str, user_id: uuid.UUID, response: StoredResponse
    ) -> None:
        self.save_calls += 1
        self._store[(key, endpoint)] = response
