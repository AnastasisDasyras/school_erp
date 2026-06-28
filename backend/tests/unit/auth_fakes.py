from __future__ import annotations

import uuid

from app.modules.auth.domain.user import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[uuid.UUID, User] = {}

    async def add(self, user: User) -> None:
        self._users[user.id] = user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)


class FakePasswordHasher:
    """No real hashing — just a reversible marker, fast and deterministic for tests."""

    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{plain_password}"


class FakeTokenIssuer:
    """Records issued tokens as plain strings encoding user_id/role — no JWT needed here."""

    def issue_access_token(self, *, user_id: uuid.UUID, role: str) -> str:
        return f"access:{user_id}:{role}"

    def issue_refresh_token(self, *, user_id: uuid.UUID, role: str) -> str:
        return f"refresh:{user_id}:{role}"

    def decode(self, token: str) -> dict[str, object]:
        kind, user_id, role = token.split(":")
        return {"sub": user_id, "role": role, "type": kind}
