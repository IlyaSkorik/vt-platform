"""Application-layer exceptions for the Organization bounded context.

The application layer speaks its **own** error vocabulary. Use cases catch the
typed domain errors and re-raise them as :class:`ApplicationError` subclasses, so
callers (a DRF edge, a CLI, a task) depend only on application-level meaning —
never on the domain's internal exception tree (ARCH-001 §7.6).

Rules: **never swallow** (``raise ... from exc`` preserves the cause) and
**framework-free** (stdlib only; each error carries a stable ``code`` the
presentation edge maps to an RFC 9457 Problem Details ``type``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from apps.organization.domain.exceptions import (
    OrganizationStateError,
    StaffInvitationStateError,
    StaffMembershipStateError,
    ValueObjectValidationError,
)

__all__ = [
    "ApplicationError",
    "InvalidInputError",
    "InvalidInvitationTokenError",
    "InvitationConflictError",
    "InvitationStateConflictError",
    "MembershipConflictError",
    "MembershipStateConflictError",
    "OrganizationNotFoundError",
    "OrganizationStateConflictError",
    "PermissionDeniedError",
    "StaffInvitationNotFoundError",
    "StaffMembershipNotFoundError",
    "UserAlreadyStaffError",
    "translate_domain_errors",
]


class ApplicationError(Exception):
    """Base class for every error the Organization application layer raises."""

    code: ClassVar[str] = "application_error"


class OrganizationNotFoundError(ApplicationError):
    """The singleton organization was expected but is not present (not seeded)."""

    code: ClassVar[str] = "organization_not_found"


class StaffMembershipNotFoundError(ApplicationError):
    """No staff membership matched the identifier/lookup a use case required."""

    code: ClassVar[str] = "staff_membership_not_found"


class StaffInvitationNotFoundError(ApplicationError):
    """No staff invitation matched the identifier/lookup a use case required."""

    code: ClassVar[str] = "staff_invitation_not_found"


class InvalidInputError(ApplicationError):
    """A command carried a value the domain refused to construct (bad id/email/role)."""

    code: ClassVar[str] = "invalid_input"


class InvalidInvitationTokenError(ApplicationError):
    """A presented invitation token did not match any open invitation.

    Deliberately opaque about *why* (unknown, revoked, or expired handled
    separately) so a caller cannot probe invitation state by guessing tokens.
    """

    code: ClassVar[str] = "invalid_invitation_token"


class UserAlreadyStaffError(ApplicationError):
    """The target user already holds an ACTIVE membership in the organization."""

    code: ClassVar[str] = "user_already_staff"


class PermissionDeniedError(ApplicationError):
    """The current actor is not permitted to perform the requested action."""

    code: ClassVar[str] = "permission_denied"


class InvitationConflictError(ApplicationError):
    """An open invitation already exists for this email in the organization."""

    code: ClassVar[str] = "invitation_conflict"


class MembershipConflictError(ApplicationError):
    """A concurrent change to the membership was detected (optimistic conflict)."""

    code: ClassVar[str] = "membership_conflict"


class OrganizationStateConflictError(ApplicationError):
    """The operation is illegal in the organization's current state."""

    code: ClassVar[str] = "organization_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class MembershipStateConflictError(ApplicationError):
    """The operation is illegal in the membership's current state."""

    code: ClassVar[str] = "membership_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class InvitationStateConflictError(ApplicationError):
    """The operation is illegal in the invitation's current state (accepted/revoked/expired)."""

    code: ClassVar[str] = "invitation_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate Organization **domain** errors into **application** errors.

    Each domain error is re-raised as its application counterpart with the
    original kept as ``__cause__``; nothing is swallowed. Programming/composition
    faults (``PolicyConfigurationError``, ``DirectConstructionError``) are
    deliberately not handled here and propagate unchanged.
    """
    try:
        yield
    except ValueObjectValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except OrganizationStateError as exc:
        raise OrganizationStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
    except StaffMembershipStateError as exc:
        raise MembershipStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
    except StaffInvitationStateError as exc:
        raise InvitationStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
