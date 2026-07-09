"""Domain exceptions for the Organization bounded context.

Typed, framework-free domain errors raised by the domain (entities, value
objects, policies) and mapped to RFC 9457 Problem Details at the presentation
edge (ARCH-001 §7.6). No Django/DRF imports.

    OrganizationDomainError                 — base for every error in this context
    ├── ValueObjectValidationError          — a value object rejected its input
    │   ├── InvalidOrganizationIdError
    │   ├── InvalidStaffMembershipIdError
    │   ├── InvalidStaffInvitationIdError
    │   ├── InvalidStaffUserIdError
    │   ├── InvalidOrganizationNameError
    │   ├── InvalidOrganizationSlugError
    │   ├── InvalidStaffEmailError
    │   └── InvalidInvitationTokenHashError
    ├── PolicyConfigurationError            — a policy was injected invalid configuration
    ├── DirectConstructionError             — an aggregate was built bypassing its factories
    ├── OrganizationStateError              — an operation illegal in the Organization's state
    │   ├── OrganizationSuspendedError
    │   └── OrganizationNotSuspendedError
    ├── StaffMembershipStateError           — an operation illegal in the membership's state
    │   ├── MembershipNotPendingError
    │   ├── MembershipAlreadyActiveError
    │   └── MembershipAlreadyRevokedError
    └── StaffInvitationStateError           — an operation illegal in the invitation's state
        ├── InvitationAlreadyAcceptedError
        ├── InvitationRevokedError
        └── InvitationExpiredError
"""

from __future__ import annotations


class OrganizationDomainError(Exception):
    """Base class for all errors raised by the Organization domain."""


class ValueObjectValidationError(OrganizationDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so callers treating construction like value
    parsing keep working, while still being catchable as a domain-specific error.
    """


class InvalidOrganizationIdError(ValueObjectValidationError):
    """The provided value is not a valid ``OrganizationId`` (must be a UUID v7)."""


class InvalidStaffMembershipIdError(ValueObjectValidationError):
    """The provided value is not a valid ``StaffMembershipId`` (must be a UUID v7)."""


class InvalidStaffInvitationIdError(ValueObjectValidationError):
    """The provided value is not a valid ``StaffInvitationId`` (must be a UUID v7)."""


class InvalidStaffUserIdError(ValueObjectValidationError):
    """The provided value is not a valid ``StaffUserId`` (must be a UUID v7)."""


class InvalidOrganizationNameError(ValueObjectValidationError):
    """The provided value is not a valid organization name (empty or too long)."""


class InvalidOrganizationSlugError(ValueObjectValidationError):
    """The provided value is not a valid organization slug (lowercase kebab-case)."""


class InvalidStaffEmailError(ValueObjectValidationError):
    """The provided value is not a syntactically valid email address."""


class InvalidInvitationTokenHashError(ValueObjectValidationError):
    """The provided value is not a valid invitation token hash (SHA-256 hex digest)."""


class PolicyConfigurationError(OrganizationDomainError, ValueError):
    """Raised when a business policy is constructed with invalid configuration.

    Policies are configured by injection (never from globals or files), so a
    nonsensical knob — a non-positive duration, for instance — is a caller/
    composition bug, not a domain-runtime condition.
    """


class DirectConstructionError(OrganizationDomainError):
    """Raised when an aggregate is built directly instead of via its factories.

    An aggregate root must be created through its ``create``/``issue``/``seed``
    factory (a new instance) or ``rehydrate`` (reconstruction from persistence),
    which alone establish the creation invariants. Calling the dataclass
    constructor directly bypasses them and is refused.
    """


class OrganizationStateError(OrganizationDomainError):
    """Base for an operation illegal in the ``Organization`` aggregate's state."""


class OrganizationSuspendedError(OrganizationStateError):
    """The organization is suspended; the operation requires an active organization."""


class OrganizationNotSuspendedError(OrganizationStateError):
    """A reactivation was attempted on an organization that is not suspended."""


class StaffMembershipStateError(OrganizationDomainError):
    """Base for an operation illegal in the ``StaffMembership`` aggregate's state."""


class MembershipNotPendingError(StaffMembershipStateError):
    """The membership is not pending; it cannot be accepted."""


class MembershipAlreadyActiveError(StaffMembershipStateError):
    """The membership is already active; it cannot be activated again."""


class MembershipAlreadyRevokedError(StaffMembershipStateError):
    """The membership is already revoked; the operation is not permitted."""


class StaffInvitationStateError(OrganizationDomainError):
    """Base for an operation illegal in the ``StaffInvitation`` aggregate's state."""


class InvitationAlreadyAcceptedError(StaffInvitationStateError):
    """The invitation has already been accepted; it cannot be accepted again."""


class InvitationRevokedError(StaffInvitationStateError):
    """The invitation was revoked and can no longer be accepted."""


class InvitationExpiredError(StaffInvitationStateError):
    """The invitation's validity window has lapsed; it can no longer be accepted."""
