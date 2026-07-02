# 0008 — Outbox pattern for reliable event publishing (SNS/SQS via LocalStack)

## Status

Accepted

## Context

Recording attendance should both (a) persist the attendance row and (b)
notify other parts of the system — eventually Notification (Phase 5) and
Reporting (Phase 5) — that it happened. The naive approach, "write to
Postgres, then call `sns.publish()`," has the **dual-write problem**: these
are two different systems with no shared transaction. If the process crashes
or the SNS call fails _after_ the DB commit but the publish never happens,
the write succeeded but nobody downstream ever finds out — a silently lost
event. If you publish _before_ committing and the commit then fails, you've
notified the world about something that never actually happened.

## Decision

- **Outbox table** (`outbox_events`): `id`, `event_type`, `payload` (JSON
  string), `status` (`pending`/`published`/`failed`), `attempts`,
  `created_at`, `published_at`.
- **The business write and the outbox write share one transaction.**
  `AttendanceService.record()` (`attendance/application/service.py`) calls
  both `AttendanceRepository.add()` and `OutboxWriter.add()` — wired onto the
  _same_ `AsyncSession` in `attendance/api/dependencies.py` — and the router
  commits once. There is no code path where the attendance row exists
  without a corresponding outbox row, or vice versa, because Postgres commits
  both or neither.
- **`OutboxWriter` is a Protocol** (`shared/outbox/ports.py`), so
  `AttendanceService` is unit-testable with `InMemoryOutboxWriter` — same
  dependency-inversion shape as every repository port in this project. The
  concrete `SqlAlchemyOutboxRepository.add()` only `flush()`es, never commits
  — committing is the caller's job, same rule as every other repository here.
- **A separate relay process** (`shared/outbox/relay.py`, its own Docker
  service `outbox-relay`) polls `outbox_events` for `PENDING` rows every 2m,
  publishes each to SNS via `MessagePublisher` (a Protocol;
  `SnsPublisher` is the boto3/LocalStack adapter), and marks it
  `published`/`failed`. The relay never touches business tables — it only
  knows about the outbox. `list_pending()` uses
  `SELECT ... FOR UPDATE SKIP LOCKED` so a second relay instance, if one were
  ever run for throughput, would claim disjoint rows instead of double-
  publishing — the same locking idea as the course-seat reservation in ADR
  0004, applied to a different problem.
- **Fan-out via SNS → two SQS queues**, each with its own DLQ
  (`infra/compose/localstack-init.sh`): `notification-queue` and
  `reporting-queue` both subscribe to the `school-erp-events` topic, each
  with a redrive policy (`maxReceiveCount: 3`) pointing at its own DLQ. This
  is provisioning only — the actual Notification/Reporting **consumers**
  that read these queues are Phase 5's job (ADR forthcoming); this phase
  proves the producer side is correct and the message is observably
  delivered.
- **Idempotency carries over unchanged.** `POST /attendance` uses the exact
  same `Idempotency-Key` mechanism as `POST /enrollments` (ADR 0007) — a
  replayed request returns the stored response without calling `record()`
  again, which also means it doesn't write a second outbox row. This matters
  _more_ here than on Enrollment: once SNS/SQS's at-least-once delivery is in
  play, idempotent producers and idempotent consumers both matter, and this
  is the producer half.

## Why

- **Atomicity is achieved by never needing a cross-system transaction.**
  Writing to one database (Postgres) is the only thing that needs to be
  atomic; "tell SNS about it" becomes a separate, retryable, at-least-once
  step performed entirely from data already durably committed. This sidesteps
  the dual-write problem instead of solving the harder problem of a
  distributed transaction across Postgres and SNS (which isn't possible to do
  atomically at all).
- **Verified live, the way that actually matters for this pattern**: recorded
  attendance, immediately checked `outbox_events` and saw a `PENDING` row
  with the correct payload; within one ~2m poll cycle the relay logs showed
  `outbox_published` and the row flipped to `published`; `awslocal sqs
receive-message` against both `notification-queue` and `reporting-queue`
  showed the identical `AttendanceRecorded` payload had fanned out to both —
  confirming the full producer pipeline end-to-end, not just that code compiles.
- **A bug caught during this verification, not after**: the `OutboxStatus`
  Postgres enum stores lowercase values (`"pending"`), but SQLAlchemy's
  default behavior for a Python `StrEnum` column sends the member _name_
  (`"PENDING"`) unless `values_callable` is set — this surfaced as the relay
  crashing on its very first poll with `invalid input value for enum
outbox_status: "PENDING"`. Fixed in `shared/outbox/orm.py` by passing
  `values_callable=lambda enum: [e.value for e in enum]`. Worth keeping in
  mind for any future `Enum` column backed by a `StrEnum` in this codebase.
- **Polling over LISTEN/NOTIFY**: simpler to reason about, no extra
  connection-management complexity for a relay that's explicitly not on any
  request's hot path. The 2m poll interval is a deliberate latency/cost
  trade-off, not a correctness requirement — LISTEN/NOTIFY would cut publish
  latency to near-zero but isn't needed for this project's purposes.

## Consequences

- End-to-end latency from "attendance recorded" to "message in SQS" is
  bounded by the poll interval (≤2m), not instantaneous — acceptable for
  notification/reporting use cases, would not be acceptable for a use case
  needing sub-second delivery.
- A `FAILED` outbox row is not automatically retried by this implementation
  — `mark_failed` just increments `attempts` and stops; the row never goes
  back to `PENDING`. A production version would either retry with backoff up
  to some attempt limit, or surface failed rows to an alert/manual-intervention
  path. Not implemented here — flagged as a known gap, consistent with how
  ADR 0007 flagged the idempotency check-then-act race as a known gap rather
  than over-engineering a corner this project doesn't need to harden yet.
- The relay is a SPOF as deployed (one container, no replicas) — acceptable
  locally; `SKIP LOCKED` already makes it safe to scale out later without
  changing the locking strategy, which is the point of having designed it
  that way now rather than retrofitting it under load.
