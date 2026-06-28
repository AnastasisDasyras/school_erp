# 0001 — Modular monolith over microservices (for now)

## Status
Accepted

## Context
We're building a School ERP to demonstrate architectural reasoning for senior/lead
interviews. Microservices are the eventual goal for two specific bounded contexts
(Notification, Reporting — see ADR 0004), but the project starts as a single deployable.

## Decision
Start with a **modular monolith**: one FastAPI process, one Postgres database, but
internally split into modules (`students`, `teachers`, `courses`, `enrollment`,
`attendance`, `grades`, `auth`) with hard boundaries enforced by clean architecture
(ADR 0002), not by network calls.

## Why
- **Faster development & debugging.** No network calls between modules, no
  distributed tracing needed yet, single `docker compose up` to run everything.
- **Single database = simple transactions.** Enrollment (insert enrollment row +
  decrement seat count) is one ACID transaction. Splitting this into two services
  would require a saga or two-phase commit — unnecessary complexity for a CRUD-heavy
  core domain with no compelling scaling reason to split yet.
- **Premature microservices are a tax, not a benefit.** Network latency, partial
  failure, distributed transactions, and deployment complexity are real costs.
  You should only pay them where there's a clear reason (independent scaling,
  independent failure domains, independent release cadence, different tech needs).
- **Modularity now means optionality later.** Because each module already has a
  clean internal boundary (ports/adapters), promoting a module to its own service
  later is a "move the code, add a network adapter" change, not a rewrite.

## Consequences
- One deploy artifact, one database, one process for the core ERP.
- Enrollment/attendance/grades transactions stay simple (single DB transaction).
- We deliberately accept that the monolith is a single failure/scaling unit for now
  — mitigated later by running multiple stateless replicas behind a load balancer
  (see Phase 2 / ADR on horizontal scaling), which gets us scaling without splitting.
- When we do split (Notification, Reporting — ADR 0004), we pick contexts that are
  read-only or side-effecting and async, specifically because they don't need to
  participate in the core transaction — avoiding the distributed-transaction problem
  instead of solving it.
