# 0009 — Extracting Notification and Reporting as standalone microservices

## Status
Accepted

## Context
Phase 4 (ADR 0008) built the producer side: attendance recording writes an
`AttendanceRecorded` event to the outbox, the relay publishes it to SNS, and
SNS fans out to two SQS queues. Phase 5's job: build the two consumers that
read those queues — completing the circuit from "event written" to "something
actually happened downstream."

The question this phase had to answer: **what makes something a genuine
microservice and not just code in a different container?**

## Decision

### What we extracted, and why these two and not others

- **Notification** (SQS → SES email) and **Reporting** (SQS → `audit_log` DB
  table) were chosen because both satisfy the only safe criteria for extraction
  without a distributed transaction: they are **async, one-directional, and
  side-effect-only**. They receive an event, do a thing, and done — no need
  to query back to the monolith, no need to participate in a transaction the
  monolith owns.
- **Auth, Students, Teachers, Courses, Enrollment** stayed in the monolith
  because extracting them would require sagas or two-phase commit to maintain
  the invariants they share (e.g. Enrollment needs a course row and a student
  row to exist; decrementing seats is part of the same transaction as the
  enrollment insert). The cost of splitting them far exceeds any benefit.
  This is the "split where it's safe" rule, not "split everything."

### What makes Reporting a genuine microservice (not just "code elsewhere")

The specific test: **does it own its own data?**

Reporting has its own Alembic history (`alembic_version_reporting` table, not
`alembic_version`) and its own migration (`audit_log` table). It never queries
the monolith's tables. The monolith never queries `audit_log`. In local dev
they share one Postgres instance — in production (Phase 8) they would be
separate RDS instances. Separate data ownership is the line between
"microservice" and "process we moved to a different container."

Notification has no DB at all — it's a pure side-effecting service (sends
email), which is the other valid shape for a microservice.

### Each service is independently deployable

Three separate Docker images, three separate build contexts, three separate
`pyproject.toml` files. `services/notification` and `services/reporting` have
zero imports from `backend/app`. They share no code — just a messaging
contract (the shape of the SNS event payload) documented implicitly in the
handler's `_parse_body` function.

### Reliability: tenacity + circuit breaker + DLQ

Notification wraps the SES call in:
- A **circuit breaker** (`pybreaker`, `fail_max=3, reset_timeout=30s`):
  if SES fails 3 times in a row, the breaker opens and short-circuits for 30s
  before retrying. Prevents hammering a broken email provider in a tight loop.
- **`tenacity` retries** (`stop_after_attempt(3), wait_exponential`):
  up to 3 in-process retries with 1/2/4s backoff before giving up and *not*
  deleting the SQS message — letting SQS handle it.
- The SQS queue has `maxReceiveCount: 3` (set in `localstack-init.sh`):
  if the consumer fails to process a message 3 receive cycles in a row,
  SQS automatically moves it to the `notification-queue-dlq`. This is the
  three-layer retry story: in-process retries (tenacity) → SQS receive-cycle
  retries → DLQ.

Reporting has the same tenacity retry wrapper but no circuit breaker (Postgres
failures are transient and don't need the breaker's "stop hammering" concern
the way an external email API does).

### Consumer pattern: long-polling, parse SNS envelope, delete-on-success

Both consumers use SQS long-polling (`WaitTimeSeconds=5`): instead of hitting
the SQS API empty-handed on every poll, we tell SQS "wait up to 5s for a
message before responding" — cuts API calls by ~12x compared to short-polling
with no meaningful latency cost.

The SNS-to-SQS path wraps the original payload in an SNS envelope:
```json
{
  "Type": "Notification",
  "Message": "<original JSON payload>",
  "MessageAttributes": {"event_type": {"Value": "AttendanceRecorded", ...}}
}
```
Both consumers' `_parse_body()` unwraps this envelope before routing to
the handler.

A message is only deleted from the queue **after** successful processing —
never before. A processing failure means the message stays in the queue and
is retried, eventually landing in the DLQ if it keeps failing. This is the
"at-least-once delivery" contract: prefer duplicate processing (handleable
with idempotency) over silent message loss.

## Why not extract Grades, Attendance as services too?

They have the same dual problem as Enrollment: recording a grade or
attendance is a write the monolith owns; other bounded contexts need to
react to it, but the write itself must be in the monolith's transaction.
That's exactly what the outbox is for — the monolith writes the event
transactionally, and the consumers react asynchronously. The consumers
don't need to *be* part of the monolith to react to its events.

## Consequences

- **End-state architecture**: 3 independently deployable units — the monolith
  (producer, 2 replicas behind Nginx) + Notification + Reporting — communicating
  only via SNS/SQS, never via direct HTTP calls or shared DB queries. This is
  the "3 independently deployable units" the plan described as the Phase 5
  goal.
- **Verified live**: `POST /attendance` → outbox row → relay publishes to SNS
  → both consumers receive the event independently → Notification logs
  `notification_sent` to SES; Reporting writes an `audit_log` row. Both
  confirmed in container logs and `psql` in a single test flow.
- **The messaging contract is implicit.** Both producer (the outbox relay's
  payload shape) and consumers (`_parse_body`'s field access) share the
  same event payload schema, but it's not formally versioned or enforced by
  a schema registry. Adding a new field to the payload is non-breaking;
  removing one requires coordinating consumer deploys — a real limitation
  for a production system with independent release cadences.
- **SES in LocalStack**: requires `ses` in `SERVICES` and a
  `ses.verify-email-identity` call in `localstack-init.sh` — otherwise SES
  rejects sends. All properly configured and idempotent on re-init.
