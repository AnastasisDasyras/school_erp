# 0011 — DB Deep-Dive: Indexes, Optimistic Locking, and Isolation Levels

## Status
Accepted

## Context
Phases 0–6 built the full distributed system. Phase 7 zooms into Postgres
itself — the layer that every other phase depends on. The goal is not to
add features, but to demonstrate that you understand *what happens inside
the database* when the system runs, and that you make deliberate choices
about locking strategy and isolation level rather than accepting defaults
blindly.

## Decisions

### 1. Composite indexes on (student_id, course_id)

Three tables — `attendance_records`, `enrollments`, `grades` — are almost
always queried by `(student_id, course_id)` together. Migration 0002/0004
added single-column indexes on each column separately. That was sufficient
for queries filtering by one column. For the composite filter, Postgres was
doing a **BitmapAnd** of two single-column bitmap index scans — two index
lookups whose result sets are intersected in memory.

Migration 0005 adds composite indexes:
- `ix_attendance_student_course` on `attendance_records(student_id, course_id)`
- `ix_enrollments_student_course` on `enrollments(student_id, course_id)`
- `ix_grades_student_course` on `grades(student_id, course_id)`

After migration, `EXPLAIN ANALYZE` on a composite filter shows a single
**Index Scan** instead of BitmapAnd. The leading column (`student_id`)
also makes these indexes useful for single-column queries on `student_id` —
the old single-column indexes are kept for `course_id`-only queries.

**Interview point**: you can't just add indexes everywhere. Each index is a
write overhead (the index B-tree is updated on every INSERT/UPDATE/DELETE).
We add composite indexes only where the access pattern justifies them — here,
the hottest query in the system (`attendance_records` by `student_id + course_id`)
clearly does.

### 2. Optimistic locking on Grades (`version` column)

Grades are written once (teacher submits a score) and occasionally corrected.
Two teachers correcting the same grade simultaneously is possible but rare.

**Decision**: optimistic locking via a `version` integer column.

The repository's `update()` method issues:
```sql
UPDATE grades
SET score=?, letter=?, version=version+1
WHERE id=? AND version=?   ← lock check
```

If another writer already incremented `version`, the WHERE matches 0 rows.
`rowcount == 0` → `StaleGradeError`. `GradeService.submit()` catches this,
reloads from DB, and retries up to 3 times.

**Why not pessimistic (`FOR UPDATE`)?** Because grade corrections are rare
and short. Holding a `SELECT ... FOR UPDATE` lock across an HTTP request
would consume a connection slot and block all other teachers from reading
that grade for the duration of the request — unnecessary overhead for a
conflict that happens maybe once a year per grade.

**Why not just let the last write win?** Because then Teacher A's correction
(score=90) would silently overwrite Teacher B's correction (score=75) with
no indication that B's read was stale. The version check prevents this.

### 3. Pessimistic locking on course seat reservation (`FOR UPDATE`)

Enrollment seat reservation is the opposite scenario: two students enrolling
for the last seat *simultaneously* is a realistic race condition (students
rush to register when a course opens). Letting both read `available_seats=1`
and both decrement would oversell the course.

**Decision**: pessimistic locking via `SELECT ... FOR UPDATE`.

`CourseRepository.get_for_update()` issues:
```sql
SELECT * FROM courses WHERE id=? FOR UPDATE;
```

The second concurrent enroller blocks at this statement until the first
transaction commits. After the first commit, the second reads the updated
`available_seats=0` and raises `CourseFullError` cleanly.

**Why not optimistic here?** Because the retry path for a failed optimistic
write on the last seat would re-read `available_seats=0` and raise
`CourseFullError` anyway — the optimistic retry bought nothing. Worse, under
high load (hundreds of students competing for the last seat), you'd get a
thundering herd of optimistic retries all failing. Pessimistic locking
serializes them cleanly at the DB.

### 4. `SKIP LOCKED` in the outbox relay

The outbox relay uses `SELECT ... FOR UPDATE SKIP LOCKED` on `outbox_events`.
This is a third pattern:

- `FOR UPDATE`: blocks other lockers — used in enrollment.
- `FOR UPDATE SKIP LOCKED`: *skips* rows already locked — used in the relay.

`SKIP LOCKED` lets two relay instances (if ever run for redundancy) each
claim disjoint batches of pending events without blocking each other. No
relay waits for the other; each gets its own slice of work.

### 5. Isolation levels

**Default: Read Committed** for all OLTP operations. Every statement sees
the latest committed data at the moment it runs. This is correct for
standard web requests where you want fresh data.

**Repeatable Read**: not used in production code in this project, but
demonstrated in `docs/architecture/db-notes.md`. Warranted when a single
transaction makes multiple reads that must see the same snapshot — e.g., a
multi-page report generation job.

**Serializable**: not used. The extra predicate-locking overhead and retry
rate are not justified by this system's write patterns. Would be relevant
for a ledger or double-spend prevention system.

**Non-repeatable read and phantom**: both documented in `db-notes.md` with
runnable psql sessions. Postgres's Repeatable Read prevents phantoms (unlike
the SQL standard, which only requires Serializable for phantom prevention) —
a Postgres-specific behaviour worth knowing.

## Consequences

- `EXPLAIN ANALYZE` demos in `docs/architecture/db-notes.md` show concrete
  cost numbers. The composite index on `attendance_records` reduces the
  composite-filter plan from BitmapAnd (two index scans + intersect) to a
  single Index Scan.
- Grades now have full optimistic-lock protection. The `version` field is
  exposed in `GradeResponse` so clients can detect concurrent modification
  (409 Conflict) and display an appropriate message.
- Migration 0005 is additive and fully reversible via `downgrade()`.
- No application isolation level is set explicitly — the SQLAlchemy session
  inherits Postgres's default (Read Committed). This is correct and
  intentional; we rely on row-level locking (`FOR UPDATE`, version column)
  rather than transaction-level isolation upgrades to handle contention.
