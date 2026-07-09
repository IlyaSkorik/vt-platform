"""Composition root for the Identity authentication edge.

The one place where the framework-free use cases are wired to their concrete
infrastructure adapters (ARCH-001 §7.3, Dependency Inversion). Views ask this
module for a fully-assembled handler or service and stay ignorant of *which*
repository, hasher, clock, or token backend sits behind the port — swapping an
adapter (or a fake, in tests) changes only this file.

Every adapter here is stateless and cheap to build, so handlers are assembled
per request rather than cached; there is no shared mutable state to reason about.
"""

from __future__ import annotations

from apps.identity.application.events import SendVerificationEmailOnUserRegistered
from apps.identity.application.handlers import (
    AuthenticateUserHandler,
    ConfirmEmailVerificationHandler,
    LogoutHandler,
    RefreshTokenHandler,
    RegisterUserHandler,
    RequestEmailVerificationHandler,
)
from apps.identity.application.handlers.user_handlers import CurrentUserHandler
from apps.identity.application.interfaces import EventPublisher, TokenService
from apps.identity.domain.events import UserRegistered
from apps.identity.domain.policies import EmailVerificationPolicy, PasswordPolicy
from apps.identity.infrastructure.auth import Argon2PasswordHasher, JWTService
from apps.identity.infrastructure.messaging import (
    DjangoEmailGateway,
    EventDispatcher,
    SignedVerificationTokenService,
)
from apps.identity.infrastructure.repositories import DjangoUserRepository
from apps.identity.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_authenticate_user_handler",
    "build_confirm_email_verification_handler",
    "build_current_user_handler",
    "build_event_publisher",
    "build_logout_handler",
    "build_refresh_token_handler",
    "build_register_user_handler",
    "build_request_email_verification_handler",
    "build_token_service",
]


def build_token_service() -> JWTService:
    """Assemble the SimpleJWT-backed :class:`TokenService` adapter."""
    return JWTService()


def build_event_publisher() -> EventPublisher:
    """Assemble the in-process :class:`EventPublisher` with its subscribers wired.

    The single place domain events are connected to their side-effect handlers:
    ``UserRegistered`` triggers the verification email. Swapping to an outbox / bus
    later replaces only the adapter built here.
    """
    dispatcher = EventDispatcher()
    send_verification_email = SendVerificationEmailOnUserRegistered(
        email_gateway=DjangoEmailGateway(),
        tokens=SignedVerificationTokenService(),
        clock=SystemClock(),
    )
    dispatcher.subscribe(UserRegistered, send_verification_email.handle)
    return dispatcher


def build_register_user_handler() -> RegisterUserHandler:
    """Assemble the registration use case with its adapters."""
    return RegisterUserHandler(
        users=DjangoUserRepository(),
        password_hasher=Argon2PasswordHasher(),
        password_policy=PasswordPolicy(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
    )


def build_confirm_email_verification_handler() -> ConfirmEmailVerificationHandler:
    """Assemble the email-confirmation use case (token → verified) with its adapters."""
    return ConfirmEmailVerificationHandler(
        users=DjangoUserRepository(),
        tokens=SignedVerificationTokenService(),
        email_verification_policy=EmailVerificationPolicy(),
        clock=SystemClock(),
    )


def build_request_email_verification_handler() -> RequestEmailVerificationHandler:
    """Assemble the (re)send-verification-link use case with its adapters."""
    return RequestEmailVerificationHandler(
        users=DjangoUserRepository(),
        tokens=SignedVerificationTokenService(),
        email_gateway=DjangoEmailGateway(),
        clock=SystemClock(),
    )


def build_authenticate_user_handler() -> AuthenticateUserHandler:
    """Assemble the login (credential-verification) use case with its adapters."""
    return AuthenticateUserHandler(
        users=DjangoUserRepository(),
        password_hasher=Argon2PasswordHasher(),
        clock=SystemClock(),
    )


def build_refresh_token_handler(tokens: TokenService | None = None) -> RefreshTokenHandler:
    """Assemble the refresh use case over the token service."""
    return RefreshTokenHandler(tokens=tokens if tokens is not None else build_token_service())


def build_logout_handler(tokens: TokenService | None = None) -> LogoutHandler:
    """Assemble the logout use case over the token service."""
    return LogoutHandler(tokens=tokens if tokens is not None else build_token_service())

def build_current_user_handler() -> CurrentUserHandler:
    """Assemble the current user retrieval use case with its adapters."""
    return CurrentUserHandler(
        users=DjangoUserRepository(),
        clock=SystemClock(),
    )
