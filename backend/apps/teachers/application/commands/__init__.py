"""Command messages for the Teacher Directory bounded context.

One command = one intent to change state = one transaction boundary. Immutable,
transport-only dataclasses; see
:mod:`apps.teachers.application.commands.teacher_commands`.
"""

from apps.teachers.application.commands.teacher_commands import (
    AddTeacherCommand,
    ArchiveTeacherCommand,
    ReactivateTeacherCommand,
    UpdateTeacherCommand,
)

__all__ = [
    "AddTeacherCommand",
    "ArchiveTeacherCommand",
    "ReactivateTeacherCommand",
    "UpdateTeacherCommand",
]
