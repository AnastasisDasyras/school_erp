import uuid

import pytest

from app.modules.teachers.application.dto import CreateTeacherInput, UpdateTeacherInput
from app.modules.teachers.application.exceptions import (
    DuplicateTeacherEmailError,
    TeacherNotFoundError,
)
from app.modules.teachers.application.service import TeacherService
from tests.unit.teacher_fakes import InMemoryTeacherRepository


@pytest.fixture
def service() -> TeacherService:
    return TeacherService(InMemoryTeacherRepository())


async def _create(service: TeacherService, email: str = "ada@example.com") -> uuid.UUID:
    view = await service.create(
        CreateTeacherInput(first_name="Ada", last_name="Lovelace", email=email, department="CS")
    )
    return view.id


async def test_create_then_get(service: TeacherService) -> None:
    teacher_id = await _create(service)
    view = await service.get(teacher_id)
    assert view.email == "ada@example.com"


async def test_create_rejects_duplicate_email(service: TeacherService) -> None:
    await _create(service)
    with pytest.raises(DuplicateTeacherEmailError):
        await _create(service)


async def test_get_missing_raises_not_found(service: TeacherService) -> None:
    with pytest.raises(TeacherNotFoundError):
        await service.get(uuid.uuid4())


async def test_update_changes_fields(service: TeacherService) -> None:
    teacher_id = await _create(service)
    updated = await service.update(
        teacher_id,
        UpdateTeacherInput(
            first_name="Augusta", last_name="King", email="augusta@example.com", department="Math"
        ),
    )
    assert updated.full_name == "Augusta King"
    assert updated.department == "Math"


async def test_deactivate(service: TeacherService) -> None:
    teacher_id = await _create(service)
    await service.deactivate(teacher_id)
    view = await service.get(teacher_id)
    assert view.is_active is False
