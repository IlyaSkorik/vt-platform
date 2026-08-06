"""Result DTOs for the Teacher Directory application layer.

Immutable, primitive-only output shapes. A handler renders the ``Teacher``
aggregate into a flat :class:`TeacherDto` so no outer layer imports the domain to
read a result. Command handlers return an :class:`OperationResultDto` (the view
plus the events produced); query handlers return views directly.

Events are **collected, not published**: a future Unit of Work commits the
aggregate and forwards the events to the outbox (ARCH-001 §4.8).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.events import DomainEvent

__all__ = ["OperationResultDto", "TeacherDto"]


@dataclass(frozen=True, slots=True)
class TeacherDto:
    """A flat, immutable read view of the ``Teacher`` aggregate."""

    id: str
    owner_id: str
    first_name: str
    last_name: str
    middle_name: str | None
    full_name: str
    role: str
    email: str | None
    phone: str | None
    #: Whether a consent for holding this adult's details is on file, and under which
    #: version of the text — exposed so the cabinet can show it rather than assume it.
    consent_recorded: bool
    consent_version: str | None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_teacher(cls, teacher: Teacher) -> TeacherDto:
        """Project ``teacher`` into a DTO, flattening its value objects."""
        return cls(
            id=teacher.id.json(),
            owner_id=teacher.owner_id.json(),
            first_name=teacher.name.first_name,
            last_name=teacher.name.last_name,
            middle_name=teacher.name.middle_name,
            full_name=teacher.name.full_name,
            role=teacher.role.value,
            email=teacher.email.value if teacher.email is not None else None,
            phone=teacher.phone.value if teacher.phone is not None else None,
            consent_recorded=teacher.consent is not None,
            consent_version=(teacher.consent.consent_version if teacher.consent is not None else None),
            status=teacher.status.value,
            archived_at=teacher.archived_at,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
            version=teacher.version,
        )


@dataclass(frozen=True, slots=True)
class OperationResultDto:
    """The outcome of a command: the affected teacher plus the events it produced."""

    teacher: TeacherDto
    events: tuple[DomainEvent, ...]
