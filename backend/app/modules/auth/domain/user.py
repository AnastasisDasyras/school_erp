from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidUserError(ValueError):
    """Raised when a User would be constructed in an invalid state."""


class Role(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


@dataclass
class User:
    """Domain entity. Holds the password *hash*, never the plaintext password.

    Hashing itself is an infrastructure concern (passlib) and stays out of this
    class — the entity only enforces "a hash must be present", not how it's computed.
    """

    id: uuid.UUID
    email: str
    password_hash: str
    role: Role
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not _EMAIL_RE.match(self.email):
            raise InvalidUserError(f"invalid email: {self.email!r}")
        if not self.password_hash:
            raise InvalidUserError("password_hash must not be empty")

    @classmethod
    def create(cls, *, email: str, password_hash: str, role: Role) -> User:
        return cls(id=uuid.uuid4(), email=email, password_hash=password_hash, role=role)

    def deactivate(self) -> None:
        self.is_active = False
