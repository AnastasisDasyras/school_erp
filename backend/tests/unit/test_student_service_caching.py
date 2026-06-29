from datetime import date

import pytest

from app.modules.students.application.cached_service import CachedStudentService
from app.modules.students.application.dto import CreateStudentInput
from app.modules.students.application.service import StudentService
from tests.unit.cache_fakes import InMemoryCache
from tests.unit.fakes import InMemoryStudentRepository


@pytest.fixture
def cache() -> InMemoryCache:
    return InMemoryCache()


@pytest.fixture
def repository() -> InMemoryStudentRepository:
    return InMemoryStudentRepository()


@pytest.fixture
def service(repository: InMemoryStudentRepository, cache: InMemoryCache) -> CachedStudentService:
    return CachedStudentService(StudentService(repository), cache)


async def test_list_is_served_from_cache_on_second_call(
    service: CachedStudentService, repository: InMemoryStudentRepository, cache: InMemoryCache
) -> None:
    await service.create(
        CreateStudentInput(
            first_name="Ada", last_name="Lovelace", email="ada@example.com",
            date_of_birth=date(1990, 1, 1),
        )
    )

    first = await service.list(offset=0, limit=10, search=None)
    # Mutate the repository directly, bypassing the service, to prove a
    # second `list()` call returns the *cached* page, not a fresh DB read.
    await repository.delete(first.items[0].id)

    second = await service.list(offset=0, limit=10, search=None)
    assert second.total == 1
    assert second.items[0].email == "ada@example.com"


async def test_create_invalidates_list_cache(
    service: CachedStudentService, cache: InMemoryCache
) -> None:
    await service.list(offset=0, limit=10, search=None)
    assert await cache.get("students:list:0:10:") is not None

    await service.create(
        CreateStudentInput(
            first_name="Grace", last_name="Hopper", email="grace@example.com",
            date_of_birth=date(1985, 5, 5),
        )
    )

    assert await cache.get("students:list:0:10:") is None
