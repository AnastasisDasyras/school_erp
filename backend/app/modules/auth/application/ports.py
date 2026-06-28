from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.auth.domain.user import User


class UserRepository(Protocol):
    """Port: application depends on this shape, never on SQLAlchemy directly."""

    async def add(self, user: User) -> None: ...

    async def get(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class PasswordHasher(Protocol):
    """Port: swap argon2/bcrypt or a fake hasher in tests without touching the service."""

    def hash(self, plain_password: str) -> str: ...

    def verify(self, plain_password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    """Port: swap the JWT library or a fake token issuer in tests."""

    def issue_access_token(self, *, user_id: uuid.UUID, role: str) -> str: ...

    def issue_refresh_token(self, *, user_id: uuid.UUID, role: str) -> str: ...

    def decode(self, token: str) -> dict[str, object]: ...
