"""Composition root for the Teacher Directory API edge.

The one place where the framework-free use cases are wired to their concrete
infrastructure adapters (ARCH-001 §7.3, Dependency Inversion). Views ask this
module for a fully-assembled handler and stay ignorant of which repository, clock,
or uuid source sits behind the port. Every adapter is stateless and cheap to build,
so handlers are assembled per request.
"""

from __future__ import annotations

from apps.teachers.application.handlers import (
    AddTeacherHandler,
    ArchiveTeacherHandler,
    GetTeacherDirectoryHandler,
    GetTeacherHandler,
    ReactivateTeacherHandler,
    UpdateTeacherHandler,
)
from apps.teachers.infrastructure.repositories import DjangoTeacherRepository
from apps.teachers.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_add_teacher_handler",
    "build_archive_teacher_handler",
    "build_get_teacher_directory_handler",
    "build_get_teacher_handler",
    "build_reactivate_teacher_handler",
    "build_update_teacher_handler",
]


def build_add_teacher_handler() -> AddTeacherHandler:
    """Assemble the add-teacher use case with its adapters."""
    return AddTeacherHandler(teachers=DjangoTeacherRepository(), clock=SystemClock(), uuids=Uuid7Generator())


def build_update_teacher_handler() -> UpdateTeacherHandler:
    """Assemble the update-teacher use case."""
    return UpdateTeacherHandler(teachers=DjangoTeacherRepository(), clock=SystemClock())


def build_archive_teacher_handler() -> ArchiveTeacherHandler:
    """Assemble the archive-teacher use case."""
    return ArchiveTeacherHandler(teachers=DjangoTeacherRepository(), clock=SystemClock())


def build_reactivate_teacher_handler() -> ReactivateTeacherHandler:
    """Assemble the reactivate-teacher use case."""
    return ReactivateTeacherHandler(teachers=DjangoTeacherRepository(), clock=SystemClock())


def build_get_teacher_handler() -> GetTeacherHandler:
    """Assemble the retrieve-teacher read use case."""
    return GetTeacherHandler(teachers=DjangoTeacherRepository())


def build_get_teacher_directory_handler() -> GetTeacherDirectoryHandler:
    """Assemble the list-directory read use case."""
    return GetTeacherDirectoryHandler(teachers=DjangoTeacherRepository())
