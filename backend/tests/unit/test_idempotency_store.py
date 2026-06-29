import uuid

from app.shared.idempotency.ports import StoredResponse
from tests.unit.idempotency_fakes import InMemoryIdempotencyStore


async def test_get_returns_none_for_unseen_key() -> None:
    store = InMemoryIdempotencyStore()
    result = await store.get(key="abc", endpoint="POST /enrollments")
    assert result is None


async def test_save_then_get_replays_stored_response() -> None:
    store = InMemoryIdempotencyStore()
    response = StoredResponse(status_code=201, body='{"id": "x"}')

    await store.save(
        key="abc", endpoint="POST /enrollments", user_id=uuid.uuid4(), response=response
    )
    result = await store.get(key="abc", endpoint="POST /enrollments")

    assert result == response


async def test_same_key_different_endpoint_does_not_collide() -> None:
    store = InMemoryIdempotencyStore()
    response = StoredResponse(status_code=201, body='{"id": "x"}')

    await store.save(
        key="abc", endpoint="POST /enrollments", user_id=uuid.uuid4(), response=response
    )
    result = await store.get(key="abc", endpoint="POST /attendance")

    assert result is None
