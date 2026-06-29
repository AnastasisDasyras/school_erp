# 0006 — Cache-aside reads with Redis, explicit invalidation on writes

## Status
Accepted

## Context
`GET /students`, `/teachers`, `/courses` are read-heavy, filter-varying list
endpoints hitting Postgres on every call. Phase 2 already made Redis a shared
dependency available to both backend replicas — the natural next step is to
actually cache something there, and to do it in a way that doesn't silently
serve stale data once writes start happening from multiple places.

## Decision
- **Cache-aside pattern**, not write-through: `app/shared/cache/cache_aside.py`'s
  `cached()` helper checks Redis first; on a miss it calls the repository,
  writes the result back to Redis with a TTL, and returns it. Reads only ever
  touch the DB on a miss.
- **`Cache` is a Protocol** (`shared/cache/ports.py`) with three methods
  (`get`, `set`, `delete_prefix`). `RedisCache` (`shared/cache/redis_cache.py`)
  is the only adapter; every service's constructor takes `cache: Cache | None
  = None` — unit tests pass `None` (or an `InMemoryCache` fake) and get
  identical behavior with zero Redis involved.
- **Each module caches only its `list()` method**, keyed by
  `"{module}:list:{offset}:{limit}:{search}"`, TTL 30s. `get(id)` (single
  resource) is intentionally *not* cached — Enrollment reads a course via
  `get_for_update` for the transaction-critical seat check, and that path must
  never see cached data.
- **Invalidation is explicit, not TTL-only.** Every write path
  (`create`/`update`/`deactivate`/`delete`) on Students/Teachers/Courses calls
  `cache.delete_prefix(...)` for its own module after the repository write —
  using `SCAN`-based prefix deletion (not `KEYS`, which blocks Redis on a
  large keyspace) so every cached page (regardless of offset/limit/search) is
  invalidated together rather than tracking each page key individually.
- **Cross-module invalidation for Courses.** `EnrollmentService.enroll()`
  mutates a course's `available_seats` directly (ADR 0004) but doesn't own
  the Courses cache. `CourseService.LIST_CACHE_PREFIX` is exported and the
  Enrollment **router** (not the service) calls
  `RedisCache(redis).delete_prefix(...)` immediately after `session.commit()`
  succeeds — invalidating *after* commit, not inside the service, so a
  transaction that rolls back never busts a cache for a write that didn't
  actually happen.

## Why
- **Cache-aside over write-through**: writes here are infrequent relative to
  reads, and the cached value (a list page) is a derived/computed shape
  (joined with totals/pagination), not a 1:1 mirror of a single row — making
  write-through awkward (you'd be caching on every write whether or not
  anyone reads that exact page/filter combination again).
- **Verified live, not just unit-tested**: `redis-cli KEYS "students:list:*"`
  showed the key appear after a first `GET /students` (miss → populate), a
  second call served the same response with a Redis hit, and `POST /students`
  immediately made the key disappear — confirmed the very next `GET` recomputed
  `total` from Postgres rather than serving the old count.
- **The cross-module Courses invalidation is the actual interesting case.**
  A naive design would have only `CourseService`'s own writes invalidate its
  cache, and silently serve a stale `available_seats` for up to 30s after
  every enrollment. This was caught and fixed *before* shipping by reasoning
  through "what else mutates a course's row besides `CourseService`?" —
  verified by hand: prime the courses cache, enroll a student, confirm the key
  is gone, and the next read shows the decremented seat count immediately
  rather than after the TTL.
- **Explicit invalidation over relying on TTL alone** because a 30s window of
  staleness is a real, visible bug for anything affecting `available_seats`
  in particular — interview-relevant point: TTL alone is "eventually
  correct," explicit invalidation on the known write paths is "correct as
  soon as the write commits," and the two are complementary (TTL is the
  safety net for invalidation paths nobody thought of yet).
- **Caching is invisible to existing tests.** Because `cache` defaults to
  `None`, all 34 pre-existing unit tests needed zero changes — caching is an
  additive concern layered onto already-tested business logic, not a rewrite
  of it.

## Consequences
- A write path that someone adds later (a new module mutating `courses` rows,
  for example) must remember to invalidate `CourseService.LIST_CACHE_PREFIX`
  — this is a manual discipline, not enforced by the type system. A
  comment on `CourseService` calls this out explicitly for future modules.
- Multi-instance correctness (Phase 2) is automatic here: both backend
  replicas share the same Redis, so an invalidation from either replica is
  visible to both — no per-instance cache to keep in sync.
- 30s TTL is a judgment call, not a measured value — fine for a portfolio
  project; a real system would tune this per-endpoint based on read
  frequency vs. staleness tolerance.
