# 0005 — Stateless services, horizontal scaling, and load balancing

## Status
Accepted

## Context
The modular monolith (ADR 0001) was, until now, a single backend process — a
single point of failure and a scaling ceiling. Phase 2's goal: run 2+ identical
backend replicas behind a load balancer locally (Nginx), as the direct local
stand-in for AWS ALB + multiple ECS Fargate tasks (Phase 8), and prove the app
is actually stateless enough for that to work correctly.

## Decision
- **Two backend replicas** (`backend1`, `backend2` in `docker-compose.yml`),
  built from the identical image, fronted by **Nginx** (`infra/nginx/nginx.conf`)
  listening on the port the frontend used to talk to the backend directly.
  Nginx's default load-balancing algorithm is round-robin across the
  `upstream backend_upstream` block.
- **Migrations run once, separately.** A new one-shot `migrate` service runs
  `alembic upgrade head` and exits; `backend1`/`backend2` declare
  `depends_on: migrate: condition: service_completed_successfully`. This
  avoids two replicas racing to run the same migration concurrently at
  startup — a problem that only appears once you have more than one replica.
- **`/health` vs `/health/ready`** (`app/main.py`): `/health` is a pure
  liveness probe (process is up). `/health/ready` additionally runs
  `SELECT 1` against Postgres and returns 503 if that fails — this is what a
  load balancer's healthcheck should hit, not `/health`, so a replica that's
  up but can't reach the database gets taken out of rotation instead of
  serving 500s.
- **`X-Instance-Id` response header** (`shared/middleware/logging.py`), set
  from `socket.gethostname()` — Docker sets a container's hostname to its
  container id for free, so this required no new config. It's also bound into
  the structured log context, so any log line can be attributed to the
  replica that produced it. This is purely an observability/demo aid — it's
  what makes round-robin distribution and the rolling-restart test visible
  rather than just "trust me."
- **Passive health checks only** (`max_fails=3 fail_timeout=10s` on each
  `server` line in the upstream block) — open-source Nginx doesn't have
  active health checks (that's an Nginx Plus feature). After 3 failed proxy
  attempts to a backend within the window, Nginx stops sending it traffic for
  10s. `proxy_next_upstream` additionally makes Nginx retry a failed request
  against the *other* upstream within the same client request when possible.

## Why
- **No in-memory session state was the precondition, not a consequence.**
  Auth was already JWT-based since Phase 1 (ADR 0003) — verified statelessly
  (HMAC signature check, no DB lookup, no server-side session) by whichever
  replica receives a request. This is why a token issued by `backend1` on
  login was accepted by `backend2` on the very next request with zero shared
  state required — proven by hand: login through the load balancer, then
  alternate `Authorization` calls and watch `X-Instance-Id` change while every
  call still returns 200.
- **Round-robin + statelessness is what makes a rolling restart safe.**
  Restarting `backend1` while hammering `/health` through Nginx produced
  **zero non-200 responses across 60 requests** spanning the full restart —
  Nginx's passive failure detection routed traffic to `backend2` during the
  gap. This is the "zero-downtime deploy" story in miniature; AWS ALB +
  ECS rolling deployments (Phase 8) do the same thing with active health
  checks instead of passive ones.
- **Separating the migration from the app startup** is a real production
  pattern, not just a workaround — it's the same reason Kubernetes has Jobs
  distinct from Deployments, and ECS has one-off `RunTask` distinct from a
  service. Doing it here, at 2 replicas, is the smallest scale at which the
  "migrations race on startup" bug actually appears, which is exactly why
  it's worth fixing now rather than retrofitting later under more replicas.
- **This Nginx config is intentionally the same shape as the AWS topology.**
  One upstream block with N stateless targets, one load balancer, one set of
  health checks — Phase 8's Terraform just swaps Nginx for an ALB target
  group and passive checks for ALB's active checks. The code under load
  (FastAPI, JWT auth) doesn't change at all.

## Consequences
- Local dev now requires `docker compose up` to bring up 2 backend containers
  instead of 1 — slightly heavier, but it's the only way to actually exercise
  multi-instance behavior (round-robin, rolling restart) before paying for
  real AWS infrastructure.
- Nginx's passive checks mean a freshly-restarted-but-still-failing backend
  isn't detected until it actually receives and fails a request — there's a
  brief window where Nginx might still attempt to route to a not-yet-ready
  replica. The app's own `/health/ready` plus Docker's `healthcheck:` block
  mitigates this for local startup ordering, but it isn't equivalent to an
  ALB's continuous active health checks.
- Any future shared/mutable state (rate-limit counters, idempotency keys,
  cache) must live in Redis/Postgres, never in process memory — this
  requirement was already anticipated by the plan but is now enforced by the
  fact that any request can land on either replica.
