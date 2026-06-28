# 0004 — Enrollment as a single ACID transaction across two aggregates

## Status
Accepted

## Context
Enrolling a student in a course must do two things atomically: insert an
`enrollments` row, and decrement the course's `available_seats`. If only one
happens — a crash between the two writes, or a bug that forgets the second
write — the system silently corrupts itself (a phantom seat, or an enrollment
with no seat ever reserved). This is also the textbook case for why we kept
Students/Teachers/Courses/Enrollment in one modular monolith (ADR 0001) instead
of splitting them into services already: across a network call, this exact
operation would need a saga or two-phase commit to stay correct.

## Decision
`EnrollmentService.enroll()` (`enrollment/application/service.py`) is
constructed with **two repositories that share the same `AsyncSession`** —
wired in `enrollment/api/dependencies.py`, which passes one session into both
`SqlAlchemyEnrollmentRepository` and `SqlAlchemyCourseRepository`. The flow:

1. Check `EnrollmentRepository.exists()` — fast pre-check, not the sole guard.
2. `CourseRepository.get_for_update(course_id)` — issues
   `SELECT ... FOR UPDATE`, taking a row lock on the course so a second
   concurrent enrollment into the last seat blocks at the database instead of
   racing on `available_seats` in two processes' memory.
3. `course.reserve_seat()` — domain method, raises `NoAvailableSeatsError` if
   the seat count is already 0. This is enforced in the entity, not just by
   `CHECK`-style application logic, so the invariant holds for any caller.
4. `CourseRepository.update(course)` + `EnrollmentRepository.add(enrollment)` —
   both flush to the same session.
5. The **router** calls `session.commit()` once, after `enroll()` returns
   successfully. If any step above raised, the router's `except` block returns
   an HTTP error and never calls `commit()` — `get_session`'s `async with
   SessionFactory()` context manager rolls back on scope exit, so a failed
   enrollment leaves zero trace: no orphaned enrollment row, no seat taken.
6. The `enrollments` table also has a DB-level `UNIQUE(student_id, course_id)`
   constraint — a second line of defense against the same race the
   `exists()` check is meant to catch, closing the gap between "check" and
   "insert" that an application-only check can't fully close.

## Why
- **One transaction, one commit point.** Because both repositories operate
  on the same session, the "insert enrollment + decrement seats" pair either
  both land or neither does — verified by hand: enrolling into a full course
  returns 409 and `GET /courses/{id}` shows `available_seats` unchanged, never
  negative.
- **Row locking (`FOR UPDATE`) over optimistic retry here.** Seat allocation
  is exactly the case pessimistic locking is for: short critical section, high
  contention expected near a course's capacity limit, and "retry the whole
  enroll flow" is more complex than "wait briefly for the lock." (Optimistic
  locking via a version column is demoed instead on Grades in a later phase,
  where contention is low and retries are cheap — see Phase 7.)
- **This is the case for NOT splitting Enrollment into its own service.**
  Splitting Course and Enrollment into separate deployables would turn this
  single transaction into a distributed one (saga, or accept eventual
  consistency with compensating actions). ADR 0001 already named this as the
  reason Notification/Reporting were chosen for extraction instead — this ADR
  is the concrete enrollment-shaped proof of that reasoning.

## Consequences
- Enrollment and Courses must stay in the same database/process as long as
  this transaction guarantee is required this way. If Enrollment ever needs
  independent scaling, the seat-reservation step would need to become a saga
  step with compensation (release the seat) — a real cost, deliberately not
  paid here.
- `get_for_update` holds a row lock for the duration of the transaction —
  under heavy concurrent enrollment into the same course, requests serialize
  on that lock. Acceptable for this project's purposes; a production system
  expecting flash-sale-style contention might pre-decrement via an atomic
  `UPDATE ... WHERE available_seats > 0` instead of read-then-write.
