from __future__ import annotations

import uuid


class GradeNotFoundError(Exception):
    def __init__(self, grade_id: uuid.UUID) -> None:
        super().__init__(f"Grade {grade_id} not found")


class GradeConflictError(Exception):
    """Raised when optimistic-lock retries are exhausted."""

    def __init__(self) -> None:
        super().__init__("Grade was modified concurrently — please retry")
