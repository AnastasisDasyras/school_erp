from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.shared.config.settings import Settings


class InvalidTokenError(Exception):
    pass


class JoseTokenIssuer:
    """Adapter implementing the TokenIssuer port using python-jose (HS256)."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._access_minutes = settings.access_token_expire_minutes
        self._refresh_minutes = settings.refresh_token_expire_minutes

    def issue_access_token(self, *, user_id: uuid.UUID, role: str) -> str:
        return self._issue(user_id=user_id, role=role, minutes=self._access_minutes, kind="access")

    def issue_refresh_token(self, *, user_id: uuid.UUID, role: str) -> str:
        return self._issue(
            user_id=user_id, role=role, minutes=self._refresh_minutes, kind="refresh"
        )

    def _issue(self, *, user_id: uuid.UUID, role: str, minutes: int, kind: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": kind,
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
