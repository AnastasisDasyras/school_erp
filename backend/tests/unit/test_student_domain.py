from datetime import date

import pytest

from app.modules.students.domain.student import InvalidStudentError, Student


def test_create_valid_student() -> None:
    student = Student.create(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        date_of_birth=date(1990, 1, 1),
    )
    assert student.full_name == "Ada Lovelace"
    assert student.is_active is True


@pytest.mark.parametrize(
    "email",
    ["not-an-email", "missing-at.com", "@missing-local.com"],
)
def test_rejects_invalid_email(email: str) -> None:
    with pytest.raises(InvalidStudentError):
        Student.create(
            first_name="Ada",
            last_name="Lovelace",
            email=email,
            date_of_birth=date(1990, 1, 1),
        )


def test_rejects_future_date_of_birth() -> None:
    with pytest.raises(InvalidStudentError):
        Student.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            date_of_birth=date(2999, 1, 1),
        )


def test_deactivate_sets_is_active_false() -> None:
    student = Student.create(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        date_of_birth=date(1990, 1, 1),
    )
    student.deactivate()
    assert student.is_active is False
