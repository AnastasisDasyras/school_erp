from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidTeacherError(ValueError):
    """Raised when a Teacher would be constructed in an invalid state."""


@dataclass
class Teacher:
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    department: str
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.first_name.strip():
            raise InvalidTeacherError("first_name must not be empty")
        if not self.last_name.strip():
            raise InvalidTeacherError("last_name must not be empty")
        if not _EMAIL_RE.match(self.email):
            raise InvalidTeacherError(f"invalid email: {self.email!r}")
        if not self.department.strip():
            raise InvalidTeacherError("department must not be empty")

    @classmethod
    def create(
        cls, *, first_name: str, last_name: str, email: str, department: str
    ) -> Teacher:
        return cls(
            id=uuid.uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            department=department,
        )

    def deactivate(self) -> None:
        self.is_active = False

    def update_details(
        self, *, first_name: str, last_name: str, email: str, department: str
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.department = department
        self._validate()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
