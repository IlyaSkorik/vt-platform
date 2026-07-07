"""Command messages for the Identity & Access bounded context.

One command = one intent to change state = one transaction boundary
(ARCH-001 §7.2, §7.4). Immutable, transport-only dataclasses; see
:mod:`apps.identity.application.commands.user_commands`. The re-exports below are
the package's public surface.
"""

from apps.identity.application.commands.user_commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    ChangePhoneCommand,
    DeleteUserCommand,
    GrantConsentCommand,
    LockUserCommand,
    RegisterUserCommand,
    RestoreUserCommand,
    UnlockUserCommand,
    VerifyEmailCommand,
    VerifyPhoneCommand,
    WithdrawConsentCommand,
)

__all__ = [
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
