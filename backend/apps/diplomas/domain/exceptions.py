"""Domain error vocabulary for the Diplomas bounded context.

Each error carries a stable ``code`` that the presentation layer maps onto an
RFC 9457 Problem Details response (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

__all__ = [
    "AssignmentConflictError",
    "AssignmentNotFoundError",
    "DiplomaError",
    "TemplateNotFoundError",
]


class DiplomaError(Exception):
    """Base class for Diplomas domain/application errors."""

    code = "diploma_error"


class TemplateNotFoundError(DiplomaError):
    """Raised when a referenced template does not exist."""

    code = "template_not_found"


class AssignmentNotFoundError(DiplomaError):
    """Raised when a referenced assignment does not exist."""

    code = "assignment_not_found"


class AssignmentConflictError(DiplomaError):
    """Raised when a (competition, nomination) pair already has an assignment."""

    code = "assignment_conflict"
