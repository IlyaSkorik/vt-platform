"""In-memory fakes for the Teacher Directory application ports.

Framework-free, database-free test doubles that structurally satisfy the ports in
:mod:`apps.teachers.application.interfaces`. Not a test module (no ``test_``
prefix), so pytest does not collect it; imported by the handler tests.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.value_objects import OwnerId, TeacherId, TeacherStatus

#: Fixed reference instant shared by the fake clock and the tests.
NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


class FakeTeacherRepository:
    """In-memory :class:`TeacherRepository` keyed by :class:`TeacherId`."""

    def __init__(self) -> None:
        self._by_id: dict[TeacherId, Teacher] = {}
        self.saved: list[Teacher] = []

    def get(self, teacher_id: TeacherId) -> Teacher | None:
        return self._by_id.get(teacher_id)

    def list_for_owner(self, owner_id: OwnerId, *, include_archived: bool = False) -> Sequence[Teacher]:
        entries = [t for t in self._by_id.values() if t.is_owned_by(owner_id)]
        if not include_archived:
            entries = [t for t in entries if t.status is TeacherStatus.ACTIVE]
        return sorted(entries, key=lambda t: t.created_at, reverse=True)

    def save(self, teacher: Teacher) -> None:
        self._by_id[teacher.id] = teacher
        self.saved.append(teacher)

    def seed(self, teacher: Teacher) -> Teacher:
        self._by_id[teacher.id] = teacher
        return teacher


class FakeClock:
    """:class:`Clock` fake frozen at a fixed instant."""

    def __init__(self, moment: datetime = NOW) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def utcnow(self) -> datetime:
        return self._moment.astimezone(UTC)


class FakeUuidGenerator:
    """:class:`UuidGenerator` fake producing fresh UUID v7 values, recording them."""

    def __init__(self) -> None:
        self.issued: list[uuid.UUID] = []

    def new(self) -> uuid.UUID:
        value = TeacherId.generate().value
        self.issued.append(value)
        return value
