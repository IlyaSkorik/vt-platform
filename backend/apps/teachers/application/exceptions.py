"""Application-layer exceptions for the Teacher Directory bounded context.

The application layer speaks its **own** error vocabulary. Use cases catch the
typed domain errors raised by value objects and the ``Teacher`` aggregate and
re-raise them as :class:`ApplicationError` subclasses, so callers (the DRF edge, a
CLI, a task) depend only on application-level meaning - never on the domain's
exception tree (ARCH-001 §7.6). Every translation preserves the cause with
``raise ... from exc``; nothing is swallowed. Standard library only.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from apps.teachers.domain.exceptions import TeacherStateError, ValueObjectValidationError

__all__ = [
    "ApplicationError",
    "InvalidInputError",
    "PermissionDeniedError",
    "TeacherNotFoundError",
    "TeacherStateConflictError",
    "translate_domain_errors",
]


class ApplicationError(Exception):
    """Base class for every error the Teacher Directory application layer raises."""

    code: ClassVar[str] = "application_error"


class TeacherNotFoundError(ApplicationError):
    """No teacher matched the identifier a use case required."""

    code: ClassVar[str] = "teacher_not_found"


class PermissionDeniedError(ApplicationError):
    """The acting user does not own the teacher they tried to read or modify."""

    code: ClassVar[str] = "permission_denied"


class InvalidInputError(ApplicationError):
    """A command carried a value the domain refused to construct."""

    code: ClassVar[str] = "invalid_input"


class TeacherStateConflictError(ApplicationError):
    """The operation is illegal in the teacher's current state.

    :attr:`domain_code` preserves the concrete domain error name for precise
    presentation mapping.
    """

    code: ClassVar[str] = "teacher_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate Teacher Directory **domain** errors into **application** errors."""
    try:
        yield
    except ValueObjectValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except TeacherStateError as exc:
        raise TeacherStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
