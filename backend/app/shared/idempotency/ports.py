from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredResponse:
    status_code: int
    body: str


class IdempotencyStore(Protocol):
    """Port: the same shape regardless of whether it's backed by Postgres
    (this project) or, e.g., Redis with a TTL in a system that doesn't need
    a permanent audit trail of idempotent requests."""

    async def get(self, *, key: str, endpoint: str) -> StoredResponse | None: ...

    async def save(
        self, *, key: str, endpoint: str, user_id: uuid.UUID, response: StoredResponse
    ) -> None: ...
