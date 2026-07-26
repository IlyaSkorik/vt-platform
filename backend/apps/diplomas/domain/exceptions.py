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
    "DiplomaNotFoundError",
    "DuplicateDiplomaError",
    "PrintJobNotFoundError",
    "PrintTemplateNotReadyError",
    "SubmissionNotFoundError",
    "TemplateNotAssignedError",
    "TemplateNotFoundError",
    "TemplateTypeMismatchError",
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


class DiplomaNotFoundError(DiplomaError):
    """Raised when a referenced diploma does not exist."""

    code = "diploma_not_found"


class SubmissionNotFoundError(DiplomaError):
    """Raised when the submission a diploma should snapshot does not exist."""

    code = "submission_not_found"


class DuplicateDiplomaError(DiplomaError):
    """Raised when a performance (submission) already has a diploma."""

    code = "diploma_conflict"


class PrintTemplateNotReadyError(DiplomaError):
    """Raised when a print package is requested but the template has no PDF."""

    code = "print_template_not_ready"


class PrintJobNotFoundError(DiplomaError):
    """Raised when a referenced print job does not exist."""

    code = "print_job_not_found"


class TemplateTypeMismatchError(DiplomaError):
    """Raised when a template is assigned to the wrong kind of document slot.

    A nomination's thank-you slot takes a ``THANK_YOU`` template and nothing else —
    otherwise a diploma layout (degree field, QR block) would be rendered as a
    courtesy letter.
    """

    code = "template_type_mismatch"


class TemplateNotAssignedError(DiplomaError):
    """Raised when generation is requested for a nomination with no template of that kind."""

    code = "template_not_assigned"
