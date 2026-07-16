"""Command & query handlers (use cases) for the Teacher Directory bounded context.

Thin orchestrators over the application ports and the ``Teacher`` aggregate: no
business rules (those live in the domain) and no persistence details (those live in
infrastructure). Every handler resolves ``now`` from the :class:`Clock`, loads or
mints the aggregate, builds validated value objects from the command's raw fields
inside :func:`translate_domain_errors`, executes the aggregate's behaviour, persists
through the :class:`TeacherRepository`, and returns an :class:`OperationResultDto`
carrying the new state and collected events.

**Ownership is an application concern.** A teacher belongs to one user; a handler
loads the aggregate and refuses (``PermissionDeniedError``) when the acting user is
not its owner - the domain never needs to know who is asking.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.teachers.application.commands import (
    AddTeacherCommand,
    ArchiveTeacherCommand,
    ReactivateTeacherCommand,
    UpdateTeacherCommand,
)
from apps.teachers.application.dto import OperationResultDto, TeacherDto
from apps.teachers.application.exceptions import TeacherNotFoundError, translate_domain_errors
from apps.teachers.application.interfaces import Clock, TeacherRepository, UuidGenerator
from apps.teachers.application.queries import GetTeacherDirectoryQuery, GetTeacherQuery
from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.events import DomainEvent
from apps.teachers.domain.value_objects import (
    EmailAddress,
    OwnerId,
    PersonName,
    PhoneNumber,
    TeacherId,
    TeacherRole,
)

__all__ = [
    "AddTeacherHandler",
    "ArchiveTeacherHandler",
    "GetTeacherDirectoryHandler",
    "GetTeacherHandler",
    "ReactivateTeacherHandler",
    "UpdateTeacherHandler",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_owner(raw: str) -> OwnerId:
    with translate_domain_errors():
        return OwnerId.from_string(raw)


def _parse_teacher_id(raw: str) -> TeacherId:
    with translate_domain_errors():
        return TeacherId.from_string(raw)


def _optional_email(raw: str | None) -> EmailAddress | None:
    if raw is None or not raw.strip():
        return None
    with translate_domain_errors():
        return EmailAddress(raw)


def _optional_phone(raw: str | None) -> PhoneNumber | None:
    if raw is None or not raw.strip():
        return None
    with translate_domain_errors():
        return PhoneNumber(raw)


def _load_owned(teachers: TeacherRepository, *, teacher_id: TeacherId, owner: OwnerId) -> Teacher:
    """Load the teacher and assert the acting user owns it, else raise.

    Absence and non-ownership are both reported as "not found" to avoid leaking the
    existence of another user's directory entries.
    """
    teacher = teachers.get(teacher_id)
    if teacher is None or not teacher.is_owned_by(owner):
        raise TeacherNotFoundError(f"No teacher {teacher_id.json()} in this directory.")
    return teacher


def _result(teacher: Teacher, events: Sequence[DomainEvent]) -> OperationResultDto:
    return OperationResultDto(teacher=TeacherDto.from_teacher(teacher), events=tuple(events))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class AddTeacherHandler:
    """Use case: add a new teacher to the acting user's personal directory."""

    def __init__(self, *, teachers: TeacherRepository, clock: Clock, uuids: UuidGenerator) -> None:
        self._teachers = teachers
        self._clock = clock
        self._uuids = uuids

    def handle(self, command: AddTeacherCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        owner = _parse_owner(command.requested_by)
        with translate_domain_errors():
            name = PersonName(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
            role = TeacherRole(command.role)
        email = _optional_email(command.email)
        phone = _optional_phone(command.phone)
        teacher_id = TeacherId.from_uuid(self._uuids.new())
        teacher, domain_events = Teacher.create(
            teacher_id=teacher_id,
            owner_id=owner,
            name=name,
            role=role,
            now=now,
            email=email,
            phone=phone,
        )
        self._teachers.save(teacher)
        return _result(teacher, domain_events)


class UpdateTeacherHandler:
    """Use case: update an existing teacher's display/contact details."""

    def __init__(self, *, teachers: TeacherRepository, clock: Clock) -> None:
        self._teachers = teachers
        self._clock = clock

    def handle(self, command: UpdateTeacherCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        owner = _parse_owner(command.requested_by)
        teacher = _load_owned(self._teachers, teacher_id=_parse_teacher_id(command.teacher_id), owner=owner)
        with translate_domain_errors():
            name = PersonName(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
            role = TeacherRole(command.role)
        email = _optional_email(command.email)
        phone = _optional_phone(command.phone)
        with translate_domain_errors():
            domain_events = teacher.update(name=name, role=role, now=now, email=email, phone=phone)
        self._teachers.save(teacher)
        return _result(teacher, domain_events)


class ArchiveTeacherHandler:
    """Use case: archive a teacher (never a physical delete)."""

    def __init__(self, *, teachers: TeacherRepository, clock: Clock) -> None:
        self._teachers = teachers
        self._clock = clock

    def handle(self, command: ArchiveTeacherCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        owner = _parse_owner(command.requested_by)
        teacher = _load_owned(self._teachers, teacher_id=_parse_teacher_id(command.teacher_id), owner=owner)
        with translate_domain_errors():
            domain_events = teacher.archive(now=now)
        self._teachers.save(teacher)
        return _result(teacher, domain_events)


class ReactivateTeacherHandler:
    """Use case: reactivate an archived teacher."""

    def __init__(self, *, teachers: TeacherRepository, clock: Clock) -> None:
        self._teachers = teachers
        self._clock = clock

    def handle(self, command: ReactivateTeacherCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        owner = _parse_owner(command.requested_by)
        teacher = _load_owned(self._teachers, teacher_id=_parse_teacher_id(command.teacher_id), owner=owner)
        with translate_domain_errors():
            domain_events = teacher.reactivate(now=now)
        self._teachers.save(teacher)
        return _result(teacher, domain_events)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


class GetTeacherHandler:
    """Read use case: retrieve a single teacher the acting user owns."""

    def __init__(self, *, teachers: TeacherRepository) -> None:
        self._teachers = teachers

    def handle(self, query: GetTeacherQuery) -> TeacherDto:
        owner = _parse_owner(query.requested_by)
        teacher = _load_owned(self._teachers, teacher_id=_parse_teacher_id(query.teacher_id), owner=owner)
        return TeacherDto.from_teacher(teacher)


class GetTeacherDirectoryHandler:
    """Read use case: list the acting user's directory entries."""

    def __init__(self, *, teachers: TeacherRepository) -> None:
        self._teachers = teachers

    def handle(self, query: GetTeacherDirectoryQuery) -> tuple[TeacherDto, ...]:
        owner = _parse_owner(query.requested_by)
        entries = self._teachers.list_for_owner(owner, include_archived=query.include_archived)
        return tuple(TeacherDto.from_teacher(teacher) for teacher in entries)
