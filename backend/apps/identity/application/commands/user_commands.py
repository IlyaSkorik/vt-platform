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
    "ConfirmEmailVerificationCommand",
    "DeleteUserCommand",
    "GrantConsentCommand",
    "LockUserCommand",
    "RegisterUserCommand",
    "RequestEmailVerificationCommand",
    "RequestPasswordResetCommand",
    "ResetPasswordCommand",
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
class ConfirmEmailVerificationCommand:
    """Confirm an email address from the signed token carried by the emailed link.

    The presentation edge collected only the opaque ``token``; the handler verifies
    its integrity through the
    :class:`~apps.identity.application.interfaces.VerificationTokenService` (which
    yields the account id and the issue instant) and then applies the domain
    verification, so the token codec never leaks into presentation.
    """

    token: str


@dataclass(frozen=True, slots=True)
class RequestEmailVerificationCommand:
    """(Re)send an email-verification link to the account owning ``email``.

    Public and unauthenticated (a user who cannot sign in because their email is
    unverified must still be able to ask for a fresh link). ``email`` names the
    target address; the handler is deliberately anti-enumeration — an unknown,
    deleted, or already-verified address is a silent no-op, so a caller cannot
    probe which addresses are registered.
    """

    email: str


@dataclass(frozen=True, slots=True)
class RequestPasswordResetCommand:
    """Begin password recovery: email a reset link to the account owning ``email``.

    Public and unauthenticated (a user who forgot their password cannot sign in).
    Like :class:`RequestEmailVerificationCommand`, the handler is deliberately
    anti-enumeration — an unknown, deleted, or unverified-email address is a silent
    no-op — so a caller cannot probe which addresses are registered.
    """

    email: str


@dataclass(frozen=True, slots=True)
class ResetPasswordCommand:
    """Set a new password from the signed token carried by the emailed reset link.

    The presentation edge collected only the opaque ``token`` and the new password;
    the handler verifies the token's integrity through the
    :class:`~apps.identity.application.interfaces.VerificationTokenService` (which
    yields the account id and the issue instant), enforces password strength, and
    applies the domain reset, so the token codec never leaks into presentation.
    """

    token: str
    new_password: str


@dataclass(frozen=True, slots=True)
class ChangeEmailCommand:
    """Replace the account's email address (resets email verification).

    ``current_password`` is re-asked at the point of change and not taken on trust
    from the session. The address is the account's recovery channel: whoever
    controls it controls the account, so a borrowed browser must not be enough to
    move it somewhere its owner cannot reach.
    """

    user_id: str
    new_email: str
    current_password: str


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
    """Change the account's own password (validated, then hashed, upstream).

    ``current_password`` is proof that the person at the keyboard is the account
    holder and not somebody who found the session already open. An operator- or
    token-driven reset, where there is no current password to give, goes through
    :class:`ResetPasswordCommand` instead.
    """

    user_id: str
    current_password: str
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
