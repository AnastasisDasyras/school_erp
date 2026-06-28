from __future__ import annotations

import uuid

from app.modules.students.application.dto import (
    CreateStudentInput,
    StudentPage,
    StudentView,
    UpdateStudentInput,
)
from app.modules.students.application.exceptions import (
    DuplicateStudentEmailError,
    StudentNotFoundError,
)
from app.modules.students.application.ports import StudentRepository
from app.modules.students.domain.student import Student


def _to_view(student: Student) -> StudentView:
    return StudentView(
        id=student.id,
        first_name=student.first_name,
        last_name=student.last_name,
        full_name=student.full_name,
        email=student.email,
        date_of_birth=student.date_of_birth,
        enrolled_on=student.enrolled_on,
        is_active=student.is_active,
    )


class StudentService:
    """Use cases for the Students bounded context.

    Depends only on the StudentRepository port — swap the adapter (Postgres,
    in-memory fake) and this class is untouched. This is what makes unit
    tests for business rules possible without a database.
    """

    def __init__(self, repository: StudentRepository) -> None:
        self._repository = repository

    async def create(self, data: CreateStudentInput) -> StudentView:
        if await self._repository.get_by_email(data.email) is not None:
            raise DuplicateStudentEmailError(data.email)

        student = Student.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            date_of_birth=data.date_of_birth,
        )
        await self._repository.add(student)
        return _to_view(student)

    async def get(self, student_id: uuid.UUID) -> StudentView:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return _to_view(student)

    async def list(self, *, offset: int, limit: int, search: str | None) -> StudentPage:
        students = await self._repository.list(offset=offset, limit=limit, search=search)
        total = await self._repository.count(search=search)
        return StudentPage(
            items=[_to_view(s) for s in students],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def update(self, student_id: uuid.UUID, data: UpdateStudentInput) -> StudentView:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        existing_with_email = await self._repository.get_by_email(data.email)
        if existing_with_email is not None and existing_with_email.id != student_id:
            raise DuplicateStudentEmailError(data.email)

        student.update_details(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            date_of_birth=data.date_of_birth,
        )

        await self._repository.update(student)
        return _to_view(student)

    async def deactivate(self, student_id: uuid.UUID) -> None:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        student.deactivate()
        await self._repository.update(student)

    async def delete(self, student_id: uuid.UUID) -> None:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        await self._repository.delete(student_id)
