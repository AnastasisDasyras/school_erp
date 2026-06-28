from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidStudentError(ValueError):
    """Raised when a Student would be constructed in an invalid state."""


@dataclass
class Student:
    """Domain entity. No FastAPI, no SQLAlchemy — just the business rules.

    Validation lives here, not in the Pydantic schema or the ORM model, so the
    rule holds no matter who creates a Student (API, a future consumer, a test).
    """

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    date_of_birth: date
    enrolled_on: date = field(default_factory=date.today)
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.first_name.strip():
            raise InvalidStudentError("first_name must not be empty")
        if not self.last_name.strip():
            raise InvalidStudentError("last_name must not be empty")
        if not _EMAIL_RE.match(self.email):
            raise InvalidStudentError(f"invalid email: {self.email!r}")
        if self.date_of_birth >= date.today():
            raise InvalidStudentError("date_of_birth must be in the past")

    @classmethod
    def create(
        cls,
        *,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: date,
    ) -> Student:
        return cls(
            id=uuid.uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            date_of_birth=date_of_birth,
        )

    def deactivate(self) -> None:
        self.is_active = False

    def update_details(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: date,
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.date_of_birth = date_of_birth
        self._validate()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
