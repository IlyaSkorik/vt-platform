"""Command messages for the Identity & Access bounded context.

A command is an **intent** to change state, expressed as immutable transport data
that crosses the boundary from presentation (or a task/CLI) into the application
layer. Each is a ``frozen``, ``slots`` dataclass carrying only primitives and
stdlib types — **never** domain value objects and **never** behaviour. The
matching handler (``application/handlers``) is responsible for turning these raw
fields into validated domain value objects and orchestrating the use case; the
command itself holds no business logic.

Design contract for every command here:

* immutable (``frozen=True``) and memory-light (``slots=True``);
* transport data only — strings, optional strings, and ``datetime`` for instants
  the presentation layer already resolved (e.g. when a verification link was
  issued, decoded from a signed token);
* fully typed, no ``Any``.

Timestamps note: :class:`VerifyEmailCommand.sent_at` and
:class:`VerifyPhoneCommand.issued_at` are supplied by the caller because the
domain evaluates verification expiry against *when the challenge was issued*, and
this application layer has no verification-token store of its own — the instant
travels with the request (typically inside the signed token the edge decodes).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "AuthenticateUserCommand",
    "ChangeEmailCommand",
    "ChangePasswordCommand",
    "ChangePhoneCommand",
    "DeleteUserCommand",
    "GrantConsentCommand",
    "LockUserCommand",
    "RegisterUserCommand",
    "RestoreUserCommand",
    "UnlockUserCommand",
    "VerifyEmailCommand",
    "VerifyPhoneCommand",
    "WithdrawConsentCommand",
]


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    """Authenticate an account by email + password (login).

    Carries only the raw credentials the presentation layer collected. The
    handler resolves the account, verifies the password through the
    :class:`~apps.identity.application.interfaces.PasswordHasher` port, and checks
    the account may establish a session — never leaking *which* of "unknown email"
    or "wrong password" failed (generic credentials error, API-000 §26).
    """

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    """Register a brand-new account from raw registration input."""

    email: str
    password: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyEmailCommand:
    """Confirm ownership of the account's current email address.

    ``sent_at`` is the instant the verification link was issued, against which the
    policy's timeout is measured.
    """

    user_id: str
    sent_at: datetime


@dataclass(frozen=True, slots=True)
class ChangeEmailCommand:
    """Replace the account's email address (resets email verification)."""

    user_id: str
    new_email: str


@dataclass(frozen=True, slots=True)
class ChangePhoneCommand:
    """Set or replace the account's phone number (resets phone verification)."""

    user_id: str
    new_phone: str


@dataclass(frozen=True, slots=True)
class VerifyPhoneCommand:
    """Confirm ownership of the account's current phone number.

    ``issued_at`` is the instant the one-time code was issued, against which the
    policy's code lifetime is measured.
    """

    user_id: str
    issued_at: datetime


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    """Set a new password for the account (validated, then hashed, upstream)."""

    user_id: str
    new_password: str


@dataclass(frozen=True, slots=True)
class GrantConsentCommand:
    """Record acceptance of a versioned consent document.

    ``consent_type`` is the string value of a domain ``ConsentType``; ``None``
    defaults to terms of service.
    """

    user_id: str
    consent_version: str
    consent_type: str | None = None


@dataclass(frozen=True, slots=True)
class WithdrawConsentCommand:
    """Revoke the account's currently-active consent."""

    user_id: str
    consent_type: str | None = None


@dataclass(frozen=True, slots=True)
class LockUserCommand:
    """Lock the account, blocking authentication.

    ``until`` bounds a temporary lock; ``None`` requests an indefinite lock.
    """

    user_id: str
    reason: str
    until: datetime | None = None


@dataclass(frozen=True, slots=True)
class UnlockUserCommand:
    """Release an active lock on the account."""

    user_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class DeleteUserCommand:
    """Soft-delete the account (reversible; retained for audit)."""

    user_id: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RestoreUserCommand:
    """Reactivate a soft-deleted account."""

    user_id: str
