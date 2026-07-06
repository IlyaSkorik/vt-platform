"""Domain exceptions for the Identity & Access bounded context.

Typed, framework-free domain errors. They are raised by the domain (entities,
value objects, services, policies) and mapped to RFC 9457 Problem Details at the
presentation edge (ARCH-001 §7.6). No Django/DRF imports.

The hierarchy is intentionally shallow:

    IdentityDomainError                     — base for every Identity domain error
    └── ValueObjectValidationError          — a value object rejected its input
        ├── InvalidUserIdError
        ├── InvalidEmailError
        ├── InvalidPhoneNumberError
        ├── InvalidFullNameError
        ├── InvalidPasswordHashError
        ├── InvalidConsentVersionError
        ├── UnsupportedLocaleError
        └── InvalidTimezoneError
"""

from __future__ import annotations


class IdentityDomainError(Exception):
    """Base class for all errors raised by the Identity domain."""


class ValueObjectValidationError(IdentityDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so that callers treating construction like any
    other value parsing continue to work, while still being catchable as a
    domain-specific error.
    """


class InvalidUserIdError(ValueObjectValidationError):
    """The provided value is not a valid ``UserId`` (must be a UUID v7)."""


class InvalidEmailError(ValueObjectValidationError):
    """The provided value is not a syntactically valid email address."""


class InvalidPhoneNumberError(ValueObjectValidationError):
    """The provided value cannot be normalized to a valid E.164 phone number."""


class InvalidFullNameError(ValueObjectValidationError):
    """The provided name parts are invalid (empty, too long, or contain disallowed characters)."""


class InvalidPasswordHashError(ValueObjectValidationError):
    """The provided value is not a valid stored password hash (e.g. looks like plaintext)."""


class InvalidConsentVersionError(ValueObjectValidationError):
    """The provided value is not a valid, comparable consent version identifier."""


class UnsupportedLocaleError(ValueObjectValidationError):
    """The provided locale is not in the set of supported locales."""


class InvalidTimezoneError(ValueObjectValidationError):
    """The provided value is not a valid IANA timezone name."""
