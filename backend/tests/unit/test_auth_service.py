import pytest

from app.modules.auth.application.dto import LoginInput, RefreshTokenInput, RegisterUserInput
from app.modules.auth.application.exceptions import (
    DuplicateUserEmailError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.modules.auth.application.service import AuthService
from app.modules.auth.domain.user import Role
from tests.unit.auth_fakes import FakePasswordHasher, FakeTokenIssuer, InMemoryUserRepository


@pytest.fixture
def service() -> AuthService:
    return AuthService(InMemoryUserRepository(), FakePasswordHasher(), FakeTokenIssuer())


async def test_register_then_login(service: AuthService) -> None:
    await service.register(
        RegisterUserInput(email="ada@example.com", password="secretpass1", role=Role.ADMIN)
    )
    pair = await service.login(LoginInput(email="ada@example.com", password="secretpass1"))
    assert pair.access_token.startswith("access:")
    assert pair.refresh_token.startswith("refresh:")


async def test_register_rejects_duplicate_email(service: AuthService) -> None:
    await service.register(
        RegisterUserInput(email="ada@example.com", password="secretpass1", role=Role.ADMIN)
    )
    with pytest.raises(DuplicateUserEmailError):
        await service.register(
            RegisterUserInput(email="ada@example.com", password="other", role=Role.STUDENT)
        )


async def test_login_rejects_wrong_password(service: AuthService) -> None:
    await service.register(
        RegisterUserInput(email="ada@example.com", password="secretpass1", role=Role.ADMIN)
    )
    with pytest.raises(InvalidCredentialsError):
        await service.login(LoginInput(email="ada@example.com", password="wrong"))


async def test_login_rejects_unknown_email(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await service.login(LoginInput(email="nobody@example.com", password="whatever"))


async def test_refresh_token_with_valid_token(service: AuthService) -> None:
    await service.register(
        RegisterUserInput(email="ada@example.com", password="secretpass1", role=Role.ADMIN)
    )
    login_pair = await service.login(LoginInput(email="ada@example.com", password="secretpass1"))

    refreshed_pair = await service.refresh(
        RefreshTokenInput(refresh_token=login_pair.refresh_token)
    )

    assert refreshed_pair.access_token.startswith("access:")
    assert refreshed_pair.refresh_token.startswith("refresh:")


async def test_refresh_token_with_empty_token(service: AuthService) -> None:
    with pytest.raises(InvalidTokenError):
        await service.refresh(RefreshTokenInput(refresh_token=""))


async def test_refresh_token_with_invalid_token(service: AuthService) -> None:
    with pytest.raises(InvalidTokenError):
        await service.refresh(
            RefreshTokenInput(refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.1.1")
        )


async def test_refresh_rejects_access_token(service: AuthService) -> None:
    await service.register(
        RegisterUserInput(email="ada@example.com", password="secretpass1", role=Role.ADMIN)
    )
    login_pair = await service.login(LoginInput(email="ada@example.com", password="secretpass1"))

    with pytest.raises(InvalidTokenError):
        await service.refresh(RefreshTokenInput(refresh_token=login_pair.access_token))