from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.application.dto import TokenPair, UserView
from app.modules.auth.domain.user import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.STUDENT


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    is_active: bool

    @classmethod
    def from_view(cls, view: UserView) -> UserResponse:
        return cls(**view.__dict__)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

    @classmethod
    def from_pair(cls, pair: TokenPair) -> TokenResponse:
        return cls(**pair.__dict__)
