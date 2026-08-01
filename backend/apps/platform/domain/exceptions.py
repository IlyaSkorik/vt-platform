"""Domain exceptions for the Platform bounded context.

Typed, framework-free errors raised by the domain and mapped to RFC 9457 Problem
Details at the presentation edge (ARCH-001 §7.6). No Django/DRF imports.

    PlatformDomainError                     - base for every error in this context
    ├── ValueObjectValidationError          - a value object rejected its input
    │   ├── InvalidPlatformAdministratorIdError
    │   └── InvalidPlatformUserIdError
    ├── DirectConstructionError             - the aggregate was built bypassing its factories
    └── PlatformAdministratorStateError     - an operation illegal in the grant's lifecycle
        ├── AdministratorAlreadyRevokedError
        └── AdministratorAlreadyActiveError
"""

from __future__ import annotations


class PlatformDomainError(Exception):
    """Base class for all errors raised by the Platform domain."""


class ValueObjectValidationError(PlatformDomainError, ValueError):
    """Raised when a value object is constructed from invalid input."""


class InvalidPlatformAdministratorIdError(ValueObjectValidationError):
    """The provided value is not a valid ``PlatformAdministratorId`` (must be a UUID v7)."""


class InvalidPlatformUserIdError(ValueObjectValidationError):
    """The provided value is not a valid ``PlatformUserId`` reference (must be a UUID v7)."""


class DirectConstructionError(PlatformDomainError):
    """Raised when the aggregate is built directly instead of via its factories."""


class PlatformAdministratorStateError(PlatformDomainError):
    """Base for an operation illegal in the administrator grant's lifecycle state."""


class AdministratorAlreadyRevokedError(PlatformAdministratorStateError):
    """The grant is already revoked."""


class AdministratorAlreadyActiveError(PlatformAdministratorStateError):
    """The grant is already active."""
