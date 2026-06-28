import uuid

import pytest

from app.modules.courses.domain.course import Course, NoAvailableSeatsError


def _course(capacity: int = 2) -> Course:
    return Course.create(title="Algorithms", teacher_id=uuid.uuid4(), capacity=capacity)


def test_create_starts_with_full_availability() -> None:
    course = _course(capacity=3)
    assert course.available_seats == 3


def test_reserve_seat_decrements_availability() -> None:
    course = _course(capacity=2)
    course.reserve_seat()
    assert course.available_seats == 1


def test_reserve_seat_raises_when_full() -> None:
    course = _course(capacity=1)
    course.reserve_seat()
    with pytest.raises(NoAvailableSeatsError):
        course.reserve_seat()


def test_release_seat_increments_availability() -> None:
    course = _course(capacity=2)
    course.reserve_seat()
    course.release_seat()
    assert course.available_seats == 2


def test_release_seat_never_exceeds_capacity() -> None:
    course = _course(capacity=2)
    course.release_seat()
    assert course.available_seats == 2
