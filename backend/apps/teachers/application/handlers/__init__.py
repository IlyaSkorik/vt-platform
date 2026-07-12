"""Command & query handlers (use cases) for the Teacher Directory bounded context.

Thin orchestrators over the application ports and the ``Teacher`` aggregate. See
:mod:`apps.teachers.application.handlers.teacher_handlers`.
"""

from apps.teachers.application.handlers.teacher_handlers import (
    AddTeacherHandler,
    ArchiveTeacherHandler,
    GetTeacherDirectoryHandler,
    GetTeacherHandler,
    ReactivateTeacherHandler,
    UpdateTeacherHandler,
)

__all__ = [
    "AddTeacherHandler",
    "ArchiveTeacherHandler",
    "GetTeacherDirectoryHandler",
    "GetTeacherHandler",
    "ReactivateTeacherHandler",
    "UpdateTeacherHandler",
]
