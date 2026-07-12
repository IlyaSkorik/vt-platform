"""Handler (use-case) tests for the Teacher Directory application layer, against fakes."""

from __future__ import annotations

import pytest

from apps.teachers.application.commands import (
    AddTeacherCommand,
    ArchiveTeacherCommand,
    ReactivateTeacherCommand,
    UpdateTeacherCommand,
)
from apps.teachers.application.exceptions import (
    InvalidInputError,
    TeacherNotFoundError,
    TeacherStateConflictError,
)
from apps.teachers.application.handlers import (
    AddTeacherHandler,
    ArchiveTeacherHandler,
    GetTeacherDirectoryHandler,
    GetTeacherHandler,
    ReactivateTeacherHandler,
    UpdateTeacherHandler,
)
from apps.teachers.application.queries import GetTeacherDirectoryQuery, GetTeacherQuery
from apps.teachers.domain.value_objects import OwnerId, TeacherId

from .fakes import FakeClock, FakeTeacherRepository, FakeUuidGenerator


def _owner_str() -> str:
    return OwnerId.from_uuid(TeacherId.generate().value).json()


class Env:
    def __init__(self) -> None:
        self.teachers = FakeTeacherRepository()
        self.clock = FakeClock()
        self.uuids = FakeUuidGenerator()

    def add(self) -> AddTeacherHandler:
        return AddTeacherHandler(teachers=self.teachers, clock=self.clock, uuids=self.uuids)

    def update(self) -> UpdateTeacherHandler:
        return UpdateTeacherHandler(teachers=self.teachers, clock=self.clock)

    def archive(self) -> ArchiveTeacherHandler:
        return ArchiveTeacherHandler(teachers=self.teachers, clock=self.clock)

    def reactivate(self) -> ReactivateTeacherHandler:
        return ReactivateTeacherHandler(teachers=self.teachers, clock=self.clock)

    def get(self) -> GetTeacherHandler:
        return GetTeacherHandler(teachers=self.teachers)

    def directory(self) -> GetTeacherDirectoryHandler:
        return GetTeacherDirectoryHandler(teachers=self.teachers)


def _add(env: Env, owner: str, *, first: str = "Anna", role: str = "Teacher") -> str:
    result = env.add().handle(AddTeacherCommand(requested_by=owner, first_name=first, last_name="Ivanova", role=role, email="anna@school.ru"))
    return result.teacher.id


class TestAdd:
    def test_adds_active_teacher(self) -> None:
        env, owner = Env(), _owner_str()
        result = env.add().handle(AddTeacherCommand(requested_by=owner, first_name="Anna", last_name="Ivanova", role="Teacher"))
        assert result.teacher.status == "ACTIVE"
        assert result.teacher.owner_id == owner
        assert len(env.teachers.saved) == 1

    def test_rejects_bad_role(self) -> None:
        env, owner = Env(), _owner_str()
        with pytest.raises(InvalidInputError):
            env.add().handle(AddTeacherCommand(requested_by=owner, first_name="Anna", last_name="Ivanova", role="  "))

    def test_rejects_bad_email(self) -> None:
        env, owner = Env(), _owner_str()
        with pytest.raises(InvalidInputError):
            env.add().handle(AddTeacherCommand(requested_by=owner, first_name="Anna", last_name="Ivanova", role="Teacher", email="nope"))


class TestUpdate:
    def test_updates_details(self) -> None:
        env, owner = Env(), _owner_str()
        teacher_id = _add(env, owner)
        result = env.update().handle(
            UpdateTeacherCommand(requested_by=owner, teacher_id=teacher_id, first_name="Anna", last_name="Sidorova", role="Director")
        )
        assert result.teacher.last_name == "Sidorova"
        assert result.teacher.role == "Director"

    def test_other_user_cannot_update(self) -> None:
        env, owner = Env(), _owner_str()
        teacher_id = _add(env, owner)
        with pytest.raises(TeacherNotFoundError):
            env.update().handle(UpdateTeacherCommand(requested_by=_owner_str(), teacher_id=teacher_id, first_name="X", last_name="Y", role="Teacher"))


class TestLifecycle:
    def test_archive_then_reactivate(self) -> None:
        env, owner = Env(), _owner_str()
        teacher_id = _add(env, owner)
        archived = env.archive().handle(ArchiveTeacherCommand(requested_by=owner, teacher_id=teacher_id))
        assert archived.teacher.status == "ARCHIVED"
        reactivated = env.reactivate().handle(ReactivateTeacherCommand(requested_by=owner, teacher_id=teacher_id))
        assert reactivated.teacher.status == "ACTIVE"

    def test_cannot_edit_archived(self) -> None:
        env, owner = Env(), _owner_str()
        teacher_id = _add(env, owner)
        env.archive().handle(ArchiveTeacherCommand(requested_by=owner, teacher_id=teacher_id))
        with pytest.raises(TeacherStateConflictError):
            env.update().handle(
                UpdateTeacherCommand(requested_by=owner, teacher_id=teacher_id, first_name="Anna", last_name="Ivanova", role="Teacher")
            )


class TestQueries:
    def test_directory_lists_only_active_by_default(self) -> None:
        env, owner = Env(), _owner_str()
        keep = _add(env, owner, first="Anna")
        drop = _add(env, owner, first="Boris")
        env.archive().handle(ArchiveTeacherCommand(requested_by=owner, teacher_id=drop))
        active = env.directory().handle(GetTeacherDirectoryQuery(requested_by=owner))
        assert [t.id for t in active] == [keep]
        with_archived = env.directory().handle(GetTeacherDirectoryQuery(requested_by=owner, include_archived=True))
        assert {t.id for t in with_archived} == {keep, drop}

    def test_directory_is_scoped_to_owner(self) -> None:
        env, owner = Env(), _owner_str()
        _add(env, owner)
        other = env.directory().handle(GetTeacherDirectoryQuery(requested_by=_owner_str()))
        assert other == ()

    def test_get_teacher(self) -> None:
        env, owner = Env(), _owner_str()
        teacher_id = _add(env, owner)
        dto = env.get().handle(GetTeacherQuery(requested_by=owner, teacher_id=teacher_id))
        assert dto.id == teacher_id

    def test_get_missing_is_not_found(self) -> None:
        env, owner = Env(), _owner_str()
        with pytest.raises(TeacherNotFoundError):
            env.get().handle(GetTeacherQuery(requested_by=owner, teacher_id=TeacherId.generate().json()))
