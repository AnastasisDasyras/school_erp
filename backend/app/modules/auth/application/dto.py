from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.modules.auth.domain.user import Role


@dataclass(frozen=True)
class RegisterUserInput:
    email: str
    password: str
    role: Role


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
