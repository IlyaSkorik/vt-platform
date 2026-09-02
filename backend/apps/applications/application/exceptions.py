"""Application-layer exceptions for the Applications (Competition Submission) context.

The application layer speaks its **own** error vocabulary. Use cases catch the
typed domain errors and re-raise them as :class:`ApplicationError` subclasses, so
callers (a DRF edge, a CLI, a task) depend only on application-level meaning -
never on the domain's internal exception tree (ARCH-001 §7.6).

Rules: **never swallow** (``raise ... from exc`` preserves the cause) and
**framework-free** (stdlib only; each error carries a stable ``code`` the
presentation edge maps to an RFC 9457 Problem Details ``type``).

Two families of error:

* **Application-only** faults that the domain cannot express because they concern
  cross-context state the domain never sees - a missing submission/competition/
  applicant, a closed competition, an unauthorized actor.
* **Translated domain** faults - :func:`translate_domain_errors` maps each domain
  error to its application counterpart, keeping the original as ``__cause__``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from apps.applications.domain.exceptions import (
    ApplicationConflictError as DomainApplicationConflictError,
)
from apps.applications.domain.exceptions import (
    ApplicationInvariantError as DomainApplicationInvariantError,
)
from apps.applications.domain.exceptions import (
    ApplicationReferenceError as DomainApplicationReferenceError,
)
from apps.applications.domain.exceptions import (
    ApplicationStateError as DomainApplicationStateError,
)
from apps.applications.domain.exceptions import (
    ApplicationValueError,
    SubmissionConflictError,
    SubmissionInvariantError,
    SubmissionReferenceError,
    SubmissionStateError,
    ValueObjectValidationError,
)

__all__ = [
    "AdditionalServiceNotAvailableError",
    "AdditionalServiceNotFoundError",
    "ApplicantNotFoundError",
    "ApplicationConflictError",
    "ApplicationError",
    "ApplicationInvariantViolationError",
    "ApplicationNotFoundError",
    "ApplicationReferenceNotFoundError",
    "ApplicationStateConflictError",
    "CompetitionClosedError",
    "CompetitionCombinationNotFoundError",
    "CompetitionNotFoundError",
    "DeadlinePassedError",
    "DuplicateChildError",
    "EducationalOrganizationNotFoundError",
    "FileTooLargeError",
    "InvalidInputError",
    "ParentGuardianRequiredError",
    "PaymentReceiptRequiredError",
    "PermissionDeniedError",
    "SubmissionChildNotFoundError",
    "SubmissionInvariantViolationError",
    "SubmissionNotFoundError",
    "SubmissionStateConflictError",
    "UnsupportedFileTypeError",
    "translate_application_domain_errors",
    "translate_domain_errors",
]


class ApplicationError(Exception):
    """Base class for every error the Applications application layer raises."""

    code: ClassVar[str] = "application_error"


# ---------------------------------------------------------------------------
# Application-only faults (cross-context state the domain never sees)
# ---------------------------------------------------------------------------


class SubmissionNotFoundError(ApplicationError):
    """No submission matched the identifier a use case required."""

    code: ClassVar[str] = "submission_not_found"


class CompetitionNotFoundError(ApplicationError):
    """The referenced competition does not exist in the Competition context."""

    code: ClassVar[str] = "competition_not_found"


class CompetitionClosedError(ApplicationError):
    """The competition is not currently accepting submissions (status or deadline)."""

    code: ClassVar[str] = "competition_closed"


class CompetitionCombinationNotFoundError(ApplicationError):
    """The Competition has no configuration/pricing for the chosen combination."""

    code: ClassVar[str] = "competition_combination_not_found"


class ApplicantNotFoundError(ApplicationError):
    """The current user does not exist in the Identity context."""

    code: ClassVar[str] = "applicant_not_found"


class FileTooLargeError(ApplicationError):
    """An uploaded file exceeds the competition's maximum size for its kind."""

    code: ClassVar[str] = "file_too_large"


class UnsupportedFileTypeError(ApplicationError):
    """An uploaded file's type/extension is not permitted for its kind."""

    code: ClassVar[str] = "unsupported_file_type"


class PermissionDeniedError(ApplicationError):
    """The current actor is not permitted to perform the requested action."""

    code: ClassVar[str] = "permission_denied"


# ---------------------------------------------------------------------------
# Translated domain faults
# ---------------------------------------------------------------------------


class InvalidInputError(ApplicationError):
    """A command carried a value the domain refused to construct (bad id/name/amount/...)."""

    code: ClassVar[str] = "invalid_input"


class SubmissionStateConflictError(ApplicationError):
    """The operation is illegal in the submission's current lifecycle state."""

    code: ClassVar[str] = "submission_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class SubmissionChildNotFoundError(ApplicationError):
    """A referenced child (participant/teacher/attachment) is not in the submission."""

    code: ClassVar[str] = "submission_child_not_found"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class DuplicateChildError(ApplicationError):
    """A child (participant/attachment) would duplicate one already in the submission."""

    code: ClassVar[str] = "duplicate_child"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class SubmissionInvariantViolationError(ApplicationError):
    """An aggregate invariant would be violated (missing performance/participant/price, count mismatch, ...)."""

    code: ClassVar[str] = "submission_invariant_violation"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate Submission **domain** errors into **application** errors.

    Each domain error is re-raised as its application counterpart with the original
    kept as ``__cause__``; nothing is swallowed. Programming/composition faults
    (``DirectConstructionError``) are deliberately not handled here and propagate
    unchanged.
    """
    try:
        yield
    except ValueObjectValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except SubmissionStateError as exc:
        raise SubmissionStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
    except SubmissionReferenceError as exc:
        raise SubmissionChildNotFoundError(str(exc), domain_code=type(exc).__name__) from exc
    except SubmissionConflictError as exc:
        raise DuplicateChildError(str(exc), domain_code=type(exc).__name__) from exc
    except SubmissionInvariantError as exc:
        raise SubmissionInvariantViolationError(str(exc), domain_code=type(exc).__name__) from exc


# ===========================================================================
# Application (order) aggregate faults
# ===========================================================================


class ApplicationNotFoundError(ApplicationError):
    """No application (order) matched the identifier a use case required."""

    code: ClassVar[str] = "application_not_found"


class EducationalOrganizationNotFoundError(ApplicationError):
    """The referenced educational organization does not exist in the Institutions context."""

    code: ClassVar[str] = "educational_organization_not_found"


class AdditionalServiceNotFoundError(ApplicationError):
    """The competition has no additional service with the requested id."""

    code: ClassVar[str] = "additional_service_not_found"


class AdditionalServiceNotAvailableError(ApplicationError):
    """The additional service is not available for any of the order's chosen formats."""

    code: ClassVar[str] = "additional_service_not_available"


class DeadlinePassedError(ApplicationError):
    """A competition deadline for the requested operation (payment/upload) has passed."""

    code: ClassVar[str] = "deadline_passed"


class MultiplePerformancesNotAllowedError(ApplicationError):
    """The festival takes one performance per application, and the order has one.

    A refusal about the competition's configuration rather than the order's state,
    which is why it lives here and not in the domain: the Application aggregate has
    no opinion on how many performances a festival wants, and reading one off a
    foreign context is exactly what the application layer is for.
    """

    code: ClassVar[str] = "multiple_performances_not_allowed"


class ParentGuardianRequiredError(ApplicationError):
    """The competition requires a verified guardian that some participant lacks."""

    code: ClassVar[str] = "parent_guardian_required"


class PaymentReceiptRequiredError(ApplicationError):
    """The competition requires a payment receipt the order does not carry yet.

    Raised at submit when the chosen formats forbid uploading the receipt later,
    and at mark-paid otherwise — the moment the proof of payment stops being
    optional depends on the organizer's ``allow_upload_later`` choice.
    """

    code: ClassVar[str] = "payment_receipt_required"


class ApplicationStateConflictError(ApplicationError):
    """The operation is illegal in the application's current order-lifecycle state."""

    code: ClassVar[str] = "application_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class ApplicationReferenceNotFoundError(ApplicationError):
    """A referenced submission/service line is not present on the application."""

    code: ClassVar[str] = "application_reference_not_found"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class ApplicationConflictError(ApplicationError):
    """A submission/service line would duplicate one already on the application."""

    code: ClassVar[str] = "application_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class ApplicationInvariantViolationError(ApplicationError):
    """An order invariant would be violated (no submissions, missing consent, not all approved)."""

    code: ClassVar[str] = "application_invariant_violation"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


@contextmanager
def translate_application_domain_errors() -> Iterator[None]:
    """Translate **Application (order)** domain errors into application errors.

    The order aggregate has its own error tree (``ApplicationDomainError``), distinct
    from the Submission tree handled by :func:`translate_domain_errors`. Each domain
    error is re-raised as its application counterpart, keeping the original as
    ``__cause__``; ``DirectApplicationConstructionError`` propagates unchanged.
    """
    try:
        yield
    except ApplicationValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    except DomainApplicationStateError as exc:
        raise ApplicationStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
    except DomainApplicationReferenceError as exc:
        raise ApplicationReferenceNotFoundError(str(exc), domain_code=type(exc).__name__) from exc
    except DomainApplicationConflictError as exc:
        raise ApplicationConflictError(str(exc), domain_code=type(exc).__name__) from exc
    except DomainApplicationInvariantError as exc:
        raise ApplicationInvariantViolationError(str(exc), domain_code=type(exc).__name__) from exc
