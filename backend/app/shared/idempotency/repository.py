from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.idempotency.orm import IdempotencyKeyModel
from app.shared.idempotency.ports import StoredResponse


class SqlAlchemyIdempotencyStore:
    """Postgres adapter. Crucially, `save()` only flushes — it never calls
    `commit()` itself. The caller (the enrollment router) commits the
    idempotency row in the *same* transaction as the business write, so a
    rollback undoes both together. Recording "this request succeeded" for a
    write that didn't actually commit would be worse than not having
    idempotency at all."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, key: str, endpoint: str) -> StoredResponse | None:
        stmt = select(IdempotencyKeyModel).where(
            IdempotencyKeyModel.key == key, IdempotencyKeyModel.endpoint == endpoint
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return StoredResponse(status_code=row.response_status, body=row.response_body)

    async def save(
        self, *, key: str, endpoint: str, user_id: uuid.UUID, response: StoredResponse
    ) -> None:
        self._session.add(
            IdempotencyKeyModel(
                key=key,
                endpoint=endpoint,
                user_id=user_id,
                response_status=response.status_code,
                response_body=response.body,
            )
        )
        await self._session.flush()
