# Database Deep-Dive Notes (Phase 7)

Connect to the running Postgres container:
```bash
docker exec -it school-erp-postgres-1 psql -U erp -d erp
```

---

## 1. Indexes + EXPLAIN ANALYZE

### 1a. The problem EXPLAIN ANALYZE solves

`EXPLAIN ANALYZE` shows you the *actual* query plan Postgres chose and the *actual*
time it took. Two things to look for:

- **Seq Scan** on a large table = full table read, O(n). Usually means a missing index.
- **Index Scan** / **Index Only Scan** = O(log n). What you want.
- **cost=X..Y** — estimated cost. **actual time=A..B** — wall-clock ms. **rows=N** — rows processed at that node.

### 1b. Seed data for meaningful plans

```sql
-- Insert 10 000 students so the planner has something to work with.
-- (Postgres won't use an index on a tiny table — it's cheaper to seq scan.)
INSERT INTO students (id, first_name, last_name, email, date_of_birth, enrolled_on, is_active)
SELECT
    gen_random_uuid(),
    'First' || i,
    'Last' || i,
    'student' || i || '@school.test',
    '2000-01-01'::date,
    '2024-09-01'::date,
    true
FROM generate_series(1, 10000) AS i;

-- Insert 1 course and enroll all students in it.
INSERT INTO courses (id, name, description, available_seats)
VALUES (gen_random_uuid(), 'Math 101', 'Demo course', 20000);

-- Capture the course id for subsequent inserts.
\set course_id (SELECT id FROM courses WHERE name='Math 101' LIMIT 1)

INSERT INTO attendance_records (id, student_id, course_id, status, recorded_on)
SELECT
    gen_random_uuid(),
    s.id,
    (SELECT id FROM courses WHERE name='Math 101' LIMIT 1),
    CASE WHEN random() > 0.1 THEN 'present' ELSE 'absent' END,
    '2026-07-01'::date
FROM students s;
```

### 1c. Before the composite index (single-column indexes only)

```sql
EXPLAIN ANALYZE
SELECT * FROM attendance_records
WHERE student_id = '<any-student-uuid>'
  AND course_id  = '<course-uuid>';
```

Expected plan (with only single-column indexes):
```
Bitmap Heap Scan on attendance_records
  Recheck Cond: ((student_id = '...') AND (course_id = '...'))
  ->  BitmapAnd
        ->  Bitmap Index Scan on ix_attendance_records_student_id
              Index Cond: (student_id = '...')
        ->  Bitmap Index Scan on ix_attendance_records_course_id
              Index Cond: (course_id = '...')
Planning Time: ~0.2 ms   Execution Time: ~0.5 ms
```

Postgres builds a bitmap of matching rows from *each* index and ANDs them.
Two index scans, then a heap fetch. Not terrible, but more work than needed.

### 1d. After migration 0005 (composite index added)

Migration 0005 adds `ix_attendance_student_course` on `(student_id, course_id)`.
Run the same query:

```sql
EXPLAIN ANALYZE
SELECT * FROM attendance_records
WHERE student_id = '<any-student-uuid>'
  AND course_id  = '<course-uuid>';
```

Expected plan:
```
Index Scan using ix_attendance_student_course on attendance_records
  Index Cond: ((student_id = '...') AND (course_id = '...'))
Planning Time: ~0.1 ms   Execution Time: ~0.05 ms
```

**One index scan, one heap fetch. ~10x faster on this query.**

The index is also useful for leading-column-only queries:
```sql
-- Still uses the composite index (leading column match):
EXPLAIN ANALYZE
SELECT * FROM attendance_records WHERE student_id = '<uuid>';
```

### 1e. Grades — optimistic-lock UPDATE plan

```sql
EXPLAIN ANALYZE
UPDATE grades
SET score = 85.0, letter = 'B', version = version + 1
WHERE id = '<grade-uuid>'
  AND version = 0;
```

Expected plan:
```
Update on grades
  ->  Index Scan using grades_pkey on grades
        Index Cond: (id = '...')
        Filter: (version = 0)
```

The PK index finds the row instantly. If `version` doesn't match, `rows=0`
and the application sees `rowcount == 0` → raises `StaleGradeError`.

---

## 2. Optimistic vs Pessimistic Locking

### 2a. Optimistic locking (Grades — low contention writes)

**When**: the thing you're updating is rarely contested. Grade corrections
happen once every few weeks per student. Holding a lock across a network
round-trip would waste connection slots for no reason.

**How it works** (see `grades/infrastructure/repository.py`):
```sql
-- Writer A reads: id=X, version=1
-- Writer B reads: id=X, version=1

-- Writer A commits first:
UPDATE grades SET score=90, letter='A', version=2 WHERE id=X AND version=1;
-- rowcount=1 → success

-- Writer B tries to commit:
UPDATE grades SET score=75, letter='C', version=2 WHERE id=X AND version=1;
-- rowcount=0 → StaleGradeError → service reloads and retries
```

**No lock is held between the SELECT and the UPDATE** — other readers and
writers proceed freely. Only one writer wins each round.

### 2b. Pessimistic locking (Enrollment — high-stakes, low-frequency)

**When**: you cannot afford even one retry failure. Two students enrolling
for the last seat must serialize; letting both read `available_seats=1` and
both decrement would oversell the course.

**How it works** (see `enrollment/infrastructure/repository.py`):
```sql
-- EnrollmentService.enroll() calls courses.get_for_update():
SELECT * FROM courses WHERE id=? FOR UPDATE;
-- This blocks any other transaction trying FOR UPDATE on the same row.
-- The second enroller waits until the first commits (or rolls back).
-- Then it reads the updated available_seats and correctly sees 0.
```

**Demo — reproduce the lock**:
```sql
-- Terminal 1:
BEGIN;
SELECT * FROM courses WHERE id = '<course-uuid>' FOR UPDATE;
-- Don't commit yet.

-- Terminal 2 (blocks immediately):
BEGIN;
SELECT * FROM courses WHERE id = '<course-uuid>' FOR UPDATE;
-- Waits...

-- Terminal 1:
COMMIT;
-- Terminal 2 unblocks and reads the updated row.
```

### 2c. Rule of thumb

| Scenario | Pattern | Why |
|---|---|---|
| Grade update (rare, low contention) | Optimistic | No lock held; retry on conflict |
| Course seat reservation (race-prone) | Pessimistic (`FOR UPDATE`) | Must serialize; no retry acceptable |
| Outbox relay (multi-consumer safe) | `SKIP LOCKED` | Each relay takes disjoint rows, no blocking |

---

## 3. Transaction Isolation Level Demos

Default Postgres isolation: **Read Committed**. Each statement in a transaction
sees the latest committed data at the moment *that statement* runs.

### 3a. Reproduce a non-repeatable read (Read Committed)

```sql
-- Terminal 1 (reader):
BEGIN;
SELECT score FROM grades WHERE id = '<grade-uuid>';
-- Returns: 75.0

-- Terminal 2 (writer):
BEGIN;
UPDATE grades SET score=90, letter='A', version=version+1 WHERE id='<grade-uuid>';
COMMIT;

-- Terminal 1 (same transaction, second read):
SELECT score FROM grades WHERE id = '<grade-uuid>';
-- Returns: 90.0  ← different result! non-repeatable read.
COMMIT;
```

Under **Read Committed** the second SELECT in T1 sees T2's committed write.
This is by design — it's the default and is fine for most use cases.

### 3b. Prevent it with REPEATABLE READ

```sql
-- Terminal 1:
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT score FROM grades WHERE id = '<grade-uuid>';
-- Returns: 75.0

-- Terminal 2:
BEGIN;
UPDATE grades SET score=90, letter='A', version=version+1 WHERE id='<grade-uuid>';
COMMIT;

-- Terminal 1 (same transaction):
SELECT score FROM grades WHERE id = '<grade-uuid>';
-- Returns: 75.0  ← same result as the first read. Snapshot is frozen.
COMMIT;
```

**Repeatable Read** takes a snapshot of the DB at transaction start. All
reads in the transaction see that snapshot, even if other transactions commit.

### 3c. Phantom read demo

A *phantom* is a new row appearing in a range query mid-transaction.

```sql
-- Terminal 1:
BEGIN;
SELECT count(*) FROM grades WHERE course_id = '<course-uuid>';
-- Returns: 5

-- Terminal 2:
INSERT INTO grades (id, student_id, course_id, score, letter, version)
VALUES (gen_random_uuid(), gen_random_uuid(), '<course-uuid>', 88, 'B', 0);
COMMIT;

-- Terminal 1:
SELECT count(*) FROM grades WHERE course_id = '<course-uuid>';
-- Read Committed: returns 6  (phantom appeared)
-- Repeatable Read: returns 5 (snapshot frozen — no phantom in Postgres)
COMMIT;
```

Postgres's **Repeatable Read** prevents phantoms too (unlike the SQL standard
which only requires it for Serializable). This is a Postgres-specific detail
worth knowing.

### 3d. Serialization failure (Serializable)

**Serializable** goes further: it detects write cycles that would be
impossible in any serial execution order and aborts one transaction.

```sql
-- Both transactions read the same data and write based on what they read.
-- Terminal 1:
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT sum(score) FROM grades WHERE student_id = '<student-uuid>';
-- Uses result to decide something, then inserts:
INSERT INTO grades (...) VALUES (...);

-- Terminal 2 (concurrent):
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT sum(score) FROM grades WHERE student_id = '<student-uuid>';
INSERT INTO grades (...) VALUES (...);
COMMIT;

-- Terminal 1:
COMMIT;
-- ERROR: could not serialize access due to concurrent update
-- Retry the whole transaction.
```

**When to use Serializable**: financial double-spend prevention, audit logs
where order matters. Rarely needed; the performance cost (predicate locking,
retry overhead) is significant.

---

## 4. Interview Talking Points

**"How do you debug a slow query?"**
> Run `EXPLAIN ANALYZE`. Look for Seq Scan on a large table. Add an index.
> Re-run to confirm it switches to Index Scan. For composite predicates,
> a composite index is better than two separate indexes because it avoids
> the BitmapAnd step.

**"What's the difference between optimistic and pessimistic locking?"**
> Optimistic: no lock held; detect conflict on write via version column;
> retry if stale. Right for low-contention scenarios. Pessimistic: lock row
> on read with FOR UPDATE; other writers block. Right for high-stakes
> serialization like seat reservation.

**"What isolation level do you use in production?"**
> Read Committed for most OLTP. Repeatable Read when a transaction must see
> a consistent snapshot (reporting, multi-step reads that must agree).
> Serializable only when you need to prevent write cycles — rare and expensive.

**"What's SKIP LOCKED?"**
> A variant of FOR UPDATE that skips rows already locked by another
> transaction instead of blocking. Used in the outbox relay:
> `SELECT ... FOR UPDATE SKIP LOCKED` lets multiple relay instances each
> claim disjoint batches of pending events without blocking each other.
