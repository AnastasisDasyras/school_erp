from app.shared.cache.cache_aside import cached
from tests.unit.cache_fakes import InMemoryCache


async def test_cached_calls_loader_on_miss_then_caches() -> None:
    cache = InMemoryCache()
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return 42

    result = await cached(
        cache,
        "key",
        ttl_seconds=30,
        loader=loader,
        to_json=str,
        from_json=int,
    )

    assert result == 42
    assert calls == 1
    assert cache.set_calls == 1


async def test_cached_skips_loader_on_hit() -> None:
    cache = InMemoryCache()
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return calls  # changes each call, so a hit returning a stale value proves caching worked

    first = await cached(cache, "key", ttl_seconds=30, loader=loader, to_json=str, from_json=int)
    second = await cached(cache, "key", ttl_seconds=30, loader=loader, to_json=str, from_json=int)

    assert first == second == 1
    assert calls == 1


async def test_delete_prefix_forces_next_call_to_miss() -> None:
    cache = InMemoryCache()
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return calls

    await cached(cache, "list:a", ttl_seconds=30, loader=loader, to_json=str, from_json=int)
    await cache.delete_prefix("list:")
    result = await cached(
        cache, "list:a", ttl_seconds=30, loader=loader, to_json=str, from_json=int
    )

    assert result == 2
    assert calls == 2
