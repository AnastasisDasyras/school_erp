# 0003 — JWT auth (access + refresh) and role-based access control

## Status
Accepted

## Context
Phase 0 stubbed `get_current_user()` to always return a fixed admin user so other
modules could be built against a stable "current user" shape before auth existed.
Phase 1 needed to replace that stub with the real thing, plus enforce who can do
what (Admin / Teacher / Student).

## Decision
- Passwords are hashed with **argon2** (via passlib), never stored or logged in
  plaintext. `PasswordHasher` is a Protocol (`auth/application/ports.py`); the
  argon2 implementation lives in `auth/infrastructure/password.py`.
- Auth issues two JWTs on login: a short-lived **access token** (15 min default)
  carrying `sub` (user id) and `role`, and a longer-lived **refresh token** (7 days).
  Both are signed HS256 with a server-side secret (`JoseTokenIssuer`).
- `get_current_user()` (`auth/current_user.py`) decodes the bearer token via
  FastAPI's `OAuth2PasswordBearer` and returns a `CurrentUser(id, role)` — the
  exact same shape the Phase 0 stub returned. Every router that depended on
  `Depends(get_current_user)` needed **zero changes** to get real auth.
- RBAC is a dependency factory: `require_role(Role.ADMIN)` returns a callable
  that wraps `get_current_user` and raises 403 if the role doesn't match. Write
  endpoints (create/update/delete) on Teachers/Courses use
  `require_role(Role.ADMIN)`; reads use plain `get_current_user` (any
  authenticated role).

## Why
- **Ports for hashing and token issuance**, not just the repository. This is
  the same dependency-inversion story as Students' `StudentRepository`, applied
  to two new concerns — and it's what let unit tests fake both (`FakePasswordHasher`,
  `FakeTokenIssuer`) and test `AuthService.register`/`login` in milliseconds,
  no real argon2 hashing or JWT signing in the test run.
- **The stub-to-real swap touched one file.** This is the actual payoff of
  Phase 0's seam comment ("modules should depend on this function, never on
  JWT details directly") — `students/api/router.py`, `teachers/api/router.py`,
  etc. import `get_current_user` from the same module path; only
  `current_user.py`'s internals changed.
- **RBAC as a dependency factory, not an `if` in every handler.** Declarative
  (`Depends(require_role(Role.ADMIN))` in the signature) keeps authorization
  visible in the route definition instead of buried in the function body, and
  it's reused identically across modules.
- **Access/refresh split** is the standard mitigation for "what if a token
  leaks" — a stolen access token expires in minutes; refresh tokens are
  intentionally not implemented as a `/refresh` endpoint yet (noted as
  follow-up) since the interview-relevant pattern (the split itself) was the
  goal for this phase.

## Consequences
- No token revocation/blocklist yet — a logged-out user's access token is
  valid until it naturally expires (15 min). Acceptable for now; full
  revocation needs a Redis-backed blocklist or short-lived tokens + refresh
  rotation, deferred to a later pass.
- `JoseTokenIssuer` is instantiated per-request in `get_current_user` (not
  cached) — cheap (no I/O), but if this becomes a hot path it's a candidate
  for a cached singleton.
