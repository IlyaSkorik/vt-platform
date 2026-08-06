"""Command messages for the Teacher Directory bounded context.

A command is an **intent** to change state, expressed as immutable transport data
crossing from presentation into the application layer. Each is a ``frozen``,
``slots`` dataclass carrying only primitives - never domain value objects and never
behaviour. ``requested_by`` is the acting user's id (the directory owner); the
handler enforces ownership.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AddTeacherCommand",
    "ArchiveTeacherCommand",
    "ReactivateTeacherCommand",
    "UpdateTeacherCommand",
]


@dataclass(frozen=True, slots=True)
class AddTeacherCommand:
    """Add a brand-new teacher to the acting user's personal directory."""

    requested_by: str
    first_name: str
    last_name: str
    role: str
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None
    #: The teacher's own consent to having their details held, obtained by whoever is
    #: entering them (LEGAL-001 §5.4). Both parts travel together or neither does.
    consent_id: str | None = None
    consent_version: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTeacherCommand:
    """Update an existing teacher's display/contact details."""

    requested_by: str
    teacher_id: str
    first_name: str
    last_name: str
    role: str
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveTeacherCommand:
    """Archive a teacher (hide from the directory, preserve for history)."""

    requested_by: str
    teacher_id: str


@dataclass(frozen=True, slots=True)
class ReactivateTeacherCommand:
    """Reactivate an archived teacher back into the directory."""

    requested_by: str
    teacher_id: str
