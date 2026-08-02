"""Unit tests for the Teacher aggregate root."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.events import TeacherAdded, TeacherArchived, TeacherReactivated, TeacherUpdated
from apps.teachers.domain.exceptions import (
    DirectConstructionError,
    IllegalTeacherStatusTransitionError,
    TeacherNotEditableError,
)
from apps.teachers.domain.value_objects import (
    EmailAddress,
    OwnerId,
    PersonName,
    PhoneNumber,
    TeacherId,
    TeacherRole,
    TeacherStatus,
)

NOW = datetime(2026, 7, 12, 9, 0, tzinfo=UTC)


def _owner() -> OwnerId:
    return OwnerId.from_uuid(TeacherId.generate().value)


def _new(*, owner: OwnerId | None = None) -> Teacher:
    teacher, _ = Teacher.create(
        teacher_id=TeacherId.generate(),
        owner_id=owner or _owner(),
        name=PersonName(first_name="Anna", last_name="Ivanova"),
        role=TeacherRole("Teacher"),
        now=NOW,
    )
    return teacher


class TestCreation:
    def test_create_is_active_and_emits_event(self) -> None:
        owner = _owner()
        teacher, events = Teacher.create(
            teacher_id=TeacherId.generate(),
            owner_id=owner,
            name=PersonName(first_name="Anna", last_name="Ivanova"),
            role=TeacherRole("Concertmaster"),
            now=NOW,
            email=EmailAddress("anna@school.ru"),
            phone=PhoneNumber("+375291234567"),
        )
        assert teacher.is_active()
        assert teacher.is_owned_by(owner)
        assert teacher.email is not None
        assert teacher.version == 1
        assert [type(e) for e in events] == [TeacherAdded]

    def test_direct_construction_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            Teacher(
                _token=object(),
                _id=TeacherId.generate(),
                _owner_id=_owner(),
                _name=PersonName(first_name="A", last_name="B"),
                _role=TeacherRole("Teacher"),
                _status=TeacherStatus.ACTIVE,
                _created_at=NOW,
                _updated_at=NOW,
            )


class TestBehaviour:
    def test_update_replaces_details(self) -> None:
        teacher = _new()
        events = teacher.update(
            name=PersonName(first_name="Anna", last_name="Sidorova"),
            role=TeacherRole("Choreographer"),
            now=NOW,
            email=EmailAddress("new@school.ru"),
        )
        assert teacher.name.last_name == "Sidorova"
        assert teacher.role == TeacherRole("Choreographer")
        assert teacher.email == EmailAddress("new@school.ru")
        assert teacher.version == 2
        assert [type(e) for e in events] == [TeacherUpdated]

    def test_archive_then_reactivate(self) -> None:
        teacher = _new()
        archive_events = teacher.archive(now=NOW)
        assert teacher.is_archived()
        assert teacher.archived_at == NOW
        assert [type(e) for e in archive_events] == [TeacherArchived]
        reactivate_events = teacher.reactivate(now=NOW)
        assert teacher.is_active()
        assert teacher.archived_at is None
        assert [type(e) for e in reactivate_events] == [TeacherReactivated]

    def test_cannot_edit_archived(self) -> None:
        teacher = _new()
        teacher.archive(now=NOW)
        with pytest.raises(TeacherNotEditableError):
            teacher.update(name=PersonName(first_name="X", last_name="Y"), role=TeacherRole("Teacher"), now=NOW)

    def test_cannot_archive_twice(self) -> None:
        teacher = _new()
        teacher.archive(now=NOW)
        with pytest.raises(IllegalTeacherStatusTransitionError):
            teacher.archive(now=NOW)

    def test_cannot_reactivate_active(self) -> None:
        teacher = _new()
        with pytest.raises(IllegalTeacherStatusTransitionError):
            teacher.reactivate(now=NOW)


class TestRehydrate:
    def test_roundtrip(self) -> None:
        original = _new()
        original.update(name=PersonName(first_name="Anna", last_name="Ivanova"), role=TeacherRole("Director"), now=NOW)
        restored = Teacher.rehydrate(
            teacher_id=original.id,
            owner_id=original.owner_id,
            name=original.name,
            role=original.role,
            status=original.status,
            created_at=original.created_at,
            updated_at=original.updated_at,
            email=original.email,
            phone=original.phone,
            archived_at=original.archived_at,
            version=original.version,
        )
        assert restored == original
        assert restored.role == TeacherRole("Director")
        assert restored.version == original.version
