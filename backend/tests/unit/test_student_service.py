import uuid
from datetime import date

import pytest

from app.modules.students.application.dto import CreateStudentInput, UpdateStudentInput
from app.modules.students.application.exceptions import (
    DuplicateStudentEmailError,
    StudentNotFoundError,
)
from app.modules.students.application.service import StudentService
from tests.unit.fakes import InMemoryStudentRepository


@pytest.fixture
def service() -> StudentService:
    return StudentService(InMemoryStudentRepository())


async def _create(service: StudentService, email: str = "ada@example.com") -> uuid.UUID:
    view = await service.create(
        CreateStudentInput(
            first_name="Ada",
            last_name="Lovelace",
            email=email,
            date_of_birth=date(1990, 1, 1),
        )
    )
    return view.id


async def test_create_then_get(service: StudentService) -> None:
    student_id = await _create(service)
    view = await service.get(student_id)
    assert view.email == "ada@example.com"


async def test_create_rejects_duplicate_email(service: StudentService) -> None:
    await _create(service)
    with pytest.raises(DuplicateStudentEmailError):
        await _create(service)


async def test_get_missing_raises_not_found(service: StudentService) -> None:
    with pytest.raises(StudentNotFoundError):
        await service.get(uuid.uuid4())


async def test_update_changes_fields(service: StudentService) -> None:
    student_id = await _create(service)
    updated = await service.update(
        student_id,
        UpdateStudentInput(
            first_name="Augusta",
            last_name="King",
            email="augusta@example.com",
            date_of_birth=date(1990, 1, 1),
        ),
    )
    assert updated.full_name == "Augusta King"


async def test_deactivate(service: StudentService) -> None:
    student_id = await _create(service)
    await service.deactivate(student_id)
    view = await service.get(student_id)
    assert view.is_active is False


async def test_list_with_search(service: StudentService) -> None:
    await _create(service, email="ada@example.com")
    await _create(service, email="grace@example.com")

    page = await service.list(offset=0, limit=10, search="grace")
    assert page.total == 1
    assert page.items[0].email == "grace@example.com"
