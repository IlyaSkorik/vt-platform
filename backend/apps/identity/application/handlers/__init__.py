"""Command handlers (use cases) for the Identity & Access bounded context.

One handler per command: thin orchestrators over the application ports and the
``User`` aggregate (ARCH-001 §7.2, §7.4). Implementations live in
:mod:`apps.identity.application.handlers.user_handlers`; the re-exports below are
the package's public surface.
"""

from apps.identity.application.handlers.session_handlers import (
    LogoutHandler,
    RefreshTokenHandler,
)
from apps.identity.application.handlers.user_handlers import (
    AuthenticateUserHandler,
    ChangeEmailHandler,
    ChangePasswordHandler,
    ChangePhoneHandler,
    DeleteUserHandler,
    GrantConsentHandler,
    LockUserHandler,
    RegisterUserHandler,
    RestoreUserHandler,
    UnlockUserHandler,
    VerifyEmailHandler,
    VerifyPhoneHandler,
    WithdrawConsentHandler,
)

__all__ = [
    "AuthenticateUserHandler",
    "ChangeEmailHandler",
    "ChangePasswordHandler",
    "ChangePhoneHandler",
    "DeleteUserHandler",
    "GrantConsentHandler",
    "LockUserHandler",
    "LogoutHandler",
    "RefreshTokenHandler",
    "RegisterUserHandler",
    "RestoreUserHandler",
    "UnlockUserHandler",
    "VerifyEmailHandler",
    "VerifyPhoneHandler",
    "WithdrawConsentHandler",
]
