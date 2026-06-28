# 0002 — Clean (hexagonal) architecture per module

## Status
Accepted

## Context
Within the modular monolith (ADR 0001), each bounded context (e.g. `students`) needs
internal structure that (a) keeps business rules testable without a database, and
(b) makes it possible to later extract a module into its own microservice without a
rewrite.

## Decision
Every module follows the same four-layer structure, demonstrated first in
`backend/app/modules/students/`:

```
students/
├── domain/          # entities + validation rules. Plain Python, zero framework imports.
├── application/     # use cases (services) + ports (Protocol interfaces) + DTOs.
├── infrastructure/  # adapters: SQLAlchemy ORM models + repository implementing the port.
└── api/             # FastAPI router, Pydantic request/response schemas, DI wiring.
```

Dependency direction is inward only: `api` → `application` → `domain`.
`infrastructure` implements interfaces defined by `application` (dependency
inversion) — `application` never imports from `infrastructure`.

## Why
- **Domain has zero framework imports.** `Student` (domain/student.py) validates its
  own invariants (email format, date of birth in the past) with plain Python/dataclasses.
  It doesn't know FastAPI or SQLAlchemy exist. Business rules are testable in
  microseconds with no I/O.
- **Application depends on a Protocol, not a concrete repository.**
  `StudentRepository` (application/ports.py) is a `typing.Protocol`. `StudentService`
  is constructed with anything satisfying that shape. In production that's
  `SqlAlchemyStudentRepository` (infrastructure/repository.py); in tests it's
  `InMemoryStudentRepository` (tests/unit/fakes.py) — a plain dict, no database.
  This is what let us write and run 12 unit tests for create/update/duplicate-email/
  search in 0.08s with zero containers.
- **One pattern, copied everywhere.** Every other module (Teachers, Courses, …)
  follows this exact layout. Reviewers and new team members only need to learn the
  pattern once.
- **This is the seam for the microservice extraction (ADR 0004).** Because
  `application` never imports `infrastructure`, moving a module to its own process
  later means: keep `domain` + `application` unchanged, write a new `infrastructure`
  adapter (own DB) and a new `api` (own FastAPI app or consumer), done.

## Consequences
- More files per module than a single `models.py` + `routes.py` would need. Accepted
  — the payoff is testability and the future extraction path, not file count.
- Every new module must follow the same four folders even when a feature feels
  "too small" for it — consistency beats local optimization here.
