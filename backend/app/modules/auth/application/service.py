from __future__ import annotations

import uuid

from app.modules.auth.application.dto import (
    LoginInput,
    RefreshTokenInput,
    RegisterUserInput,
    TokenPair,
    UserView,
)
from app.modules.auth.application.exceptions import (
    DuplicateUserEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.modules.auth.application.ports import PasswordHasher, TokenIssuer, UserRepository
from app.modules.auth.domain.user import User


def _to_view(user: User) -> UserView:
    return UserView(id=user.id, email=user.email, role=user.role, is_active=user.is_active)


class AuthService:
    """Use cases for registration and login.

    Depends only on ports (UserRepository, PasswordHasher, TokenIssuer) — none of
    them are FastAPI/passlib/jose-specific here, so this class is unit-testable
    with fakes for all three.
    """

    def __init__(
        self,
        repository: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
    ) -> None:
        self._repository = repository
        self._hasher = hasher
        self._tokens = tokens

    async def register(self, data: RegisterUserInput) -> UserView:
        if await self._repository.get_by_email(data.email) is not None:
            raise DuplicateUserEmailError(data.email)

        user = User.create(
            email=data.email,
            password_hash=self._hasher.hash(data.password),
            role=data.role,
        )
        await self._repository.add(user)
        return _to_view(user)

    async def login(self, data: LoginInput) -> TokenPair:
        user = await self._repository.get_by_email(data.email)
        if user is None or not self._hasher.verify(data.password, user.password_hash):
            raise InvalidCredentialsError(data.email)
        if not user.is_active:
            raise InactiveUserError(user.id)

        return TokenPair(
            access_token=self._tokens.issue_access_token(user_id=user.id, role=user.role.value),
            refresh_token=self._tokens.issue_refresh_token(user_id=user.id, role=user.role.value),
        )
        
    async def refresh(self, data: RefreshTokenInput) -> TokenPair:
        decoded_token = self._tokens.decode(data.refresh_token)
        if decoded_token.get("type") != "refresh":
            raise InvalidTokenError(data.refresh_token)

        try:
            user_id = uuid.UUID(str(decoded_token.get('sub')))
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError(data.refresh_token) from exc

        user = await self._repository.get(user_id)
        if user is None:
            raise InvalidTokenError(data.refresh_token)
        if not user.is_active:
            raise InactiveUserError(user.id)

        return TokenPair(
            access_token=self._tokens.issue_access_token(user_id=user.id, role=user.role.value),
            refresh_token=self._tokens.issue_refresh_token(user_id=user.id, role=user.role.value),
        )

