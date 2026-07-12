"""Domain exceptions for the Teacher Directory bounded context.

Typed, framework-free domain errors raised by the domain (the ``Teacher``
aggregate and its value objects) and mapped to RFC 9457 Problem Details at the
presentation edge (ARCH-001 §7.6). No Django/DRF imports.

    TeacherDirectoryDomainError                  - base for every error in this context
    ├── ValueObjectValidationError               - a value object rejected its input
    │   ├── InvalidTeacherIdError
    │   ├── InvalidOwnerIdError
    │   ├── InvalidPersonNameError
    │   ├── InvalidTeacherRoleError
    │   ├── InvalidEmailAddressError
    │   └── InvalidPhoneNumberError
    ├── DirectConstructionError                  - the aggregate was built bypassing its factories
    └── TeacherStateError                        - an operation illegal in the Teacher's lifecycle
        ├── TeacherNotEditableError
        └── IllegalTeacherStatusTransitionError
"""

from __future__ import annotations


class TeacherDirectoryDomainError(Exception):
    """Base class for all errors raised by the Teacher Directory domain."""


# ---------------------------------------------------------------------------
# Value-object validation
# ---------------------------------------------------------------------------


class ValueObjectValidationError(TeacherDirectoryDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so callers treating construction like value
    parsing keep working, while still being catchable as a domain-specific error.
    """


class InvalidTeacherIdError(ValueObjectValidationError):
    """The provided value is not a valid ``TeacherId`` (must be a UUID v7)."""


class InvalidOwnerIdError(ValueObjectValidationError):
    """The provided value is not a valid ``OwnerId`` reference (must be a UUID v7)."""


class InvalidPersonNameError(ValueObjectValidationError):
    """The provided value is not a valid person name (empty parts or over-long fields)."""


class InvalidTeacherRoleError(ValueObjectValidationError):
    """The provided value is not a valid teacher role (empty or too long)."""


class InvalidEmailAddressError(ValueObjectValidationError):
    """The provided value is not a valid email address."""


class InvalidPhoneNumberError(ValueObjectValidationError):
    """The provided value is not a valid phone number."""


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class DirectConstructionError(TeacherDirectoryDomainError):
    """Raised when the ``Teacher`` aggregate is built directly instead of via its factories.

    The aggregate root must be created through its ``create`` factory (a new
    instance) or ``rehydrate`` (reconstruction from persistence). Calling the
    dataclass constructor directly bypasses the creation invariants and is refused.
    """


# ---------------------------------------------------------------------------
# Lifecycle state
# ---------------------------------------------------------------------------


class TeacherStateError(TeacherDirectoryDomainError):
    """Base for an operation illegal in the ``Teacher`` aggregate's lifecycle state."""


class TeacherNotEditableError(TeacherStateError):
    """A teacher's details were edited while the teacher is archived.

    An archived directory entry is read-only; reactivate it before editing.
    """


class IllegalTeacherStatusTransitionError(TeacherStateError):
    """The requested lifecycle transition is not legal from the current status."""
