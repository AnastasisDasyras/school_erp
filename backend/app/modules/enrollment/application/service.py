from __future__ import annotations

from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.application.ports import CourseRepository
from app.modules.courses.domain.course import NoAvailableSeatsError
from app.modules.enrollment.application.dto import EnrollInput, EnrollmentView
from app.modules.enrollment.application.exceptions import AlreadyEnrolledError, CourseFullError
from app.modules.enrollment.application.ports import EnrollmentRepository
from app.modules.enrollment.domain.enrollment import Enrollment


def _to_view(enrollment: Enrollment) -> EnrollmentView:
    return EnrollmentView(
        id=enrollment.id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        enrolled_on=enrollment.enrolled_on,
    )


class EnrollmentService:
    """The transaction-boundary demo for this project.

    `enroll()` does two things that must succeed or fail together: insert an
    enrollment row, and decrement the course's available_seats. Both
    repositories share the *same* AsyncSession (injected by the API-layer
    dependency wiring), so both writes are flushed in one DB transaction —
    the router commits once, after this method returns. If seat reservation
    raises, nothing commits: no orphaned enrollment, no phantom seat loss.

    `get_for_update` issues `SELECT ... FOR UPDATE` so two concurrent
    enrollments into the last seat serialize at the DB instead of racing on
    available_seats in application memory.
    """

    def __init__(
        self,
        enrollments: EnrollmentRepository,
        courses: CourseRepository,
    ) -> None:
        self._enrollments = enrollments
        self._courses = courses

    async def enroll(self, data: EnrollInput) -> EnrollmentView:
        if await self._enrollments.exists(student_id=data.student_id, course_id=data.course_id):
            raise AlreadyEnrolledError(data.student_id, data.course_id)

        course = await self._courses.get_for_update(data.course_id)
        if course is None:
            raise CourseNotFoundError(data.course_id)

        try:
            course.reserve_seat()
        except NoAvailableSeatsError as exc:
            raise CourseFullError(data.course_id) from exc

        await self._courses.update(course)

        enrollment = Enrollment.create(student_id=data.student_id, course_id=data.course_id)
        await self._enrollments.add(enrollment)

        return _to_view(enrollment)
