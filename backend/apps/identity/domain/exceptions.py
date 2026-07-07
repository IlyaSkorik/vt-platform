"""Domain exceptions for the Identity & Access bounded context.

Typed, framework-free domain errors. They are raised by the domain (entities,
value objects, services, policies) and mapped to RFC 9457 Problem Details at the
presentation edge (ARCH-001 §7.6). No Django/DRF imports.

The hierarchy is intentionally shallow:

    IdentityDomainError                     — base for every Identity domain error
    ├── ValueObjectValidationError          — a value object rejected its input
    │   ├── InvalidUserIdError
    │   ├── InvalidEmailError
    │   ├── InvalidPhoneNumberError
    │   ├── InvalidFullNameError
    │   ├── InvalidPasswordHashError
    │   ├── InvalidConsentVersionError
    │   ├── UnsupportedLocaleError
    │   └── InvalidTimezoneError
    ├── PolicyConfigurationError            — a policy was injected invalid configuration
    ├── PolicyViolationError                — a business policy rejected an operation
    │   └── WeakPasswordError
    ├── DirectConstructionError             — the User aggregate was built bypassing its factories
    └── UserStateError                      — an operation is illegal in the aggregate's current state
        ├── UserDeletedError
        ├── UserNotDeletedError
        ├── EmailAlreadyVerifiedError
        ├── EmailNotChangedError
        ├── PhoneNotSetError
        ├── PhoneAlreadyVerifiedError
        ├── PhoneNotChangedError
        ├── VerificationExpiredError
        ├── UserNotLockedError
        ├── ConsentNotGrantedError
        └── StaleConsentError
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


class PolicyConfigurationError(IdentityDomainError, ValueError):
    """Raised when a business policy is constructed with invalid configuration.

    Policies are configured by injection (never from globals or files), so a
    nonsensical knob — a non-positive duration, a maximum below a minimum — is a
    caller/composition bug, not a domain-runtime condition. Subclasses
    :class:`ValueError` so it reads naturally at the composition root while still
    being catchable as an Identity domain error.
    """


class PolicyViolationError(IdentityDomainError):
    """Base class for a business policy rejecting an operation at runtime.

    Distinct from :class:`ValueObjectValidationError` (a value that cannot exist)
    and :class:`PolicyConfigurationError` (a misconfigured policy): the inputs are
    individually valid, but a *business rule* forbids the operation. Mapped to RFC
    9457 Problem Details at the presentation edge (ARCH-001 §7.6).
    """


class WeakPasswordError(PolicyViolationError):
    """A proposed password does not satisfy the active :class:`PasswordPolicy`.

    Carries the machine-readable ``violations`` (the string values of the policy's
    ``PasswordViolation`` reasons) so the edge can render precise, localizable
    guidance instead of a single opaque message. The type is kept free of any
    ``policies`` import to avoid a domain-internal cycle; the tuple holds plain
    strings, which the ``PasswordViolation`` string-enum members already are.
    """

    def __init__(self, violations: tuple[str, ...]) -> None:
        self.violations: tuple[str, ...] = violations
        detail = ", ".join(violations) if violations else "unspecified reason"
        super().__init__(f"Password does not satisfy the policy: {detail}.")


class DirectConstructionError(IdentityDomainError):
    """Raised when :class:`~apps.identity.domain.entities.User` is built directly.

    The aggregate root must be created through ``User.register`` (a new account) or
    ``User.rehydrate`` (reconstruction from persistence), which alone establish the
    creation invariants. Calling the dataclass constructor directly bypasses them
    and is therefore refused.
    """


class UserStateError(IdentityDomainError):
    """Base for an operation that is illegal in the User aggregate's current state.

    The inputs are individually valid, but the aggregate's lifecycle forbids the
    transition (e.g. verifying an already-verified email, mutating a deleted user).
    Mapped to RFC 9457 Problem Details at the presentation edge (ARCH-001 §7.6).
    """


class UserDeletedError(UserStateError):
    """The operation is not permitted because the user is soft-deleted."""


class UserNotDeletedError(UserStateError):
    """A restore was attempted on a user that is not soft-deleted."""


class EmailAlreadyVerifiedError(UserStateError):
    """The email address is already verified; it cannot be verified again."""


class EmailNotChangedError(UserStateError):
    """The supplied email is identical to the current one; the change is a no-op."""


class PhoneNotSetError(UserStateError):
    """A phone operation was attempted, but the user has no phone number set."""


class PhoneAlreadyVerifiedError(UserStateError):
    """The phone number is already verified; it cannot be verified again."""


class PhoneNotChangedError(UserStateError):
    """The supplied phone number is identical to the current one; the change is a no-op."""


class VerificationExpiredError(UserStateError):
    """The verification link or code has expired and can no longer confirm ownership."""


class UserNotLockedError(UserStateError):
    """An unlock was attempted on a user that is not currently locked."""


class ConsentNotGrantedError(UserStateError):
    """Consent withdrawal was attempted, but the user has no active consent."""


class StaleConsentError(UserStateError):
    """The consent version being granted is older than the current version in force."""
