# 0007 — Idempotency keys for safe client retries

## Status
Accepted

## Context
`POST /enrollments` (and any future non-idempotent write — recording
attendance, submitting a grade) has a retry problem: if a client sends the
request, the server processes it successfully, but the response is lost in
transit (timeout, proxy blip, client crash before reading the response), the
client cannot tell whether the operation actually happened. A naive retry of
the same request risks double-executing the side effect. Enrollment happens
to have a *partial* natural guard (`AlreadyEnrolledError` from the unique
`(student_id, course_id)` constraint, ADR 0004), but that guard only prevents
duplicate rows — it doesn't let the client recover the original response, and
operations without a natural uniqueness constraint have no guard at all.

## Decision
- **`idempotency_keys` table**, keyed on `(key, endpoint)` — not `key` alone,
  so a client accidentally reusing a key across two different operations
  doesn't get one operation's stored response replayed for the other.
  Columns: `user_id`, `response_status`, `response_body`, `created_at`.
- **`IdempotencyStore` is a Protocol** (`shared/idempotency/ports.py`) with
  `get`/`save`; `SqlAlchemyIdempotencyStore` is the Postgres adapter — same
  ports-and-adapters shape as every repository in this project.
- **Optional, header-driven.** The client sends `Idempotency-Key: <uuid>` on
  `POST /enrollments`. If absent, the endpoint behaves exactly as before
  (ADR 0004) — idempotency is opt-in per request, not a forced behavior.
- **Check-then-act, but committed together.** The router first calls
  `idempotency_store.get(key, endpoint)`. On a hit, it replays the stored
  `(status_code, body)` immediately — `enroll()` is never called again — and
  sets an `Idempotency-Replayed: true` response header so this is observable,
  not silent. On a miss, `enroll()` runs as normal, and
  `idempotency_store.save(...)` is called **before** `session.commit()` —
  both the enrollment write and the idempotency record land in the same
  transaction. If the enrollment fails (course full, etc.), the function
  returns before `save()` is ever reached, so no idempotency row is written
  for a request that didn't succeed — a retry after a genuine failure is
  correctly treated as a fresh attempt, not a replay.

## Why
- **`(key, endpoint)` over `key` alone**: this is the difference between "this
  exact logical operation already ran" and "this string was seen before" —
  the latter is a much weaker (and surprising) guarantee if a client ever
  reuses key generation across endpoints.
- **Saving in the same transaction as the business write is the entire point.**
  If idempotency were recorded in a separate transaction (or worse, after
  `commit()`), a crash between the two commits would leave the business write
  applied but the idempotency record missing — the next retry would
  re-run the operation believing it hadn't happened yet, defeating the
  mechanism. Verified by hand: the table only ever contains rows for
  enrollments that actually exist (checked via `psql`), because both
  `IdempotencyKeyModel.add()` and the enrollment write flush to the same
  session and commit together.
- **Replay over re-validation.** On a key hit, the original response is
  returned byte-for-byte (deserialized from the stored JSON) rather than
  re-running business logic — this is what makes the guarantee strong: even
  if the underlying data changed between the two requests (e.g. the course
  filled up in between), the client sees the *original* outcome, which is
  the only outcome consistent with "this already happened."
- **Verified live**: enrolling once with `Idempotency-Key: my-idem-key-001`
  decremented `available_seats` from 3 to 2; retrying with the identical key
  returned the same enrollment `id` with `Idempotency-Replayed: true`, and
  `available_seats` stayed at 2 — confirming no double-decrement. A retry
  with *no* key correctly fell through to the natural 409
  `AlreadyEnrolledError` guard instead.

## Consequences
- There's a narrow race between `get()` and `save()`: two concurrent retries
  with the same key could both pass the "not found" check before either
  commits. This project relies on the `(key, endpoint)` primary key to make
  the second `save()` fail at commit time rather than silently double-saving
  — a real production system would want to catch that unique-violation and
  translate it into "treat as a replay" rather than surfacing a raw 500;
  not implemented here, called out as a known gap.
- No expiry on idempotency records yet — `idempotency_keys` grows unbounded.
  A production system would TTL these (a client only needs to retry within a
  reasonable window, e.g. 24h) — straightforward to add with a periodic
  cleanup job or, if moved to Redis, a native TTL.
- Only wired into `POST /enrollments` so far — the same pattern (header →
  store check → save-before-commit) is the template for Phase 4's `POST
  /attendance`, where idempotency matters even more once SNS/SQS's
  at-least-once delivery means a consumer might reprocess a message that
  re-triggers the same API call.
