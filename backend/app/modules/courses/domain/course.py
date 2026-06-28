from __future__ import annotations

import uuid
from dataclasses import dataclass


class InvalidCourseError(ValueError):
    """Raised when a Course would be constructed in an invalid state."""


class NoAvailableSeatsError(Exception):
    """Raised when attempting to enroll into a full course."""


@dataclass
class Course:
    id: uuid.UUID
    title: str
    teacher_id: uuid.UUID
    capacity: int
    available_seats: int
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.title.strip():
            raise InvalidCourseError("title must not be empty")
        if self.capacity <= 0:
            raise InvalidCourseError("capacity must be positive")
        if not (0 <= self.available_seats <= self.capacity):
            raise InvalidCourseError("available_seats must be between 0 and capacity")

    @classmethod
    def create(cls, *, title: str, teacher_id: uuid.UUID, capacity: int) -> Course:
        return cls(
            id=uuid.uuid4(),
            title=title,
            teacher_id=teacher_id,
            capacity=capacity,
            available_seats=capacity,
        )

    def deactivate(self) -> None:
        self.is_active = False

    def update_details(self, *, title: str, teacher_id: uuid.UUID, capacity: int) -> None:
        if capacity < self.capacity - self.available_seats:
            raise InvalidCourseError("capacity cannot be lower than seats already taken")
        taken = self.capacity - self.available_seats
        self.title = title
        self.teacher_id = teacher_id
        self.capacity = capacity
        self.available_seats = capacity - taken
        self._validate()

    def reserve_seat(self) -> None:
        """Domain invariant: never let available_seats go negative.

        Enforced here (not just by the DB) so the rule holds for any caller,
        and the enrollment service can rely on this raising instead of
        re-checking arithmetic itself.
        """
        if self.available_seats <= 0:
            raise NoAvailableSeatsError(self.id)
        self.available_seats -= 1

    def release_seat(self) -> None:
        if self.available_seats < self.capacity:
            self.available_seats += 1
