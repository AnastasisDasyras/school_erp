import uuid

import pytest

from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.domain.course import Course
from app.modules.enrollment.application.dto import EnrollInput
from app.modules.enrollment.application.exceptions import AlreadyEnrolledError, CourseFullError
from app.modules.enrollment.application.service import EnrollmentService
from tests.unit.enrollment_fakes import InMemoryCourseRepository, InMemoryEnrollmentRepository


@pytest.fixture
def courses() -> InMemoryCourseRepository:
    return InMemoryCourseRepository()


@pytest.fixture
def service(courses: InMemoryCourseRepository) -> EnrollmentService:
    return EnrollmentService(InMemoryEnrollmentRepository(), courses)


async def _seed_course(courses: InMemoryCourseRepository, capacity: int = 1) -> uuid.UUID:
    course = Course.create(title="Algorithms", teacher_id=uuid.uuid4(), capacity=capacity)
    await courses.add(course)
    return course.id


async def test_enroll_decrements_available_seats(
    service: EnrollmentService, courses: InMemoryCourseRepository
) -> None:
    course_id = await _seed_course(courses, capacity=2)
    student_id = uuid.uuid4()

    await service.enroll(EnrollInput(student_id=student_id, course_id=course_id))

    course = await courses.get(course_id)
    assert course is not None
    assert course.available_seats == 1


async def test_enroll_rejects_when_course_full(
    service: EnrollmentService, courses: InMemoryCourseRepository
) -> None:
    course_id = await _seed_course(courses, capacity=1)
    await service.enroll(EnrollInput(student_id=uuid.uuid4(), course_id=course_id))

    with pytest.raises(CourseFullError):
        await service.enroll(EnrollInput(student_id=uuid.uuid4(), course_id=course_id))

    # Critical assertion for the "rollback" story: a failed enrollment must not
    # leave available_seats touched — the second call raised before any write.
    course = await courses.get(course_id)
    assert course is not None
    assert course.available_seats == 0


async def test_enroll_rejects_duplicate_enrollment(
    service: EnrollmentService, courses: InMemoryCourseRepository
) -> None:
    course_id = await _seed_course(courses, capacity=5)
    student_id = uuid.uuid4()
    await service.enroll(EnrollInput(student_id=student_id, course_id=course_id))

    with pytest.raises(AlreadyEnrolledError):
        await service.enroll(EnrollInput(student_id=student_id, course_id=course_id))

    course = await courses.get(course_id)
    assert course is not None
    assert course.available_seats == 4  # only the first enroll took a seat


async def test_enroll_rejects_unknown_course(service: EnrollmentService) -> None:
    with pytest.raises(CourseNotFoundError):
        await service.enroll(EnrollInput(student_id=uuid.uuid4(), course_id=uuid.uuid4()))
