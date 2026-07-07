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

from apps.identity.application.handlers import (
    AuthenticateUserHandler,
    LogoutHandler,
    RefreshTokenHandler,
    RegisterUserHandler,
)
from apps.identity.application.interfaces import TokenService
from apps.identity.domain.policies import PasswordPolicy
from apps.identity.infrastructure.auth import Argon2PasswordHasher, JWTService
from apps.identity.infrastructure.repositories import DjangoUserRepository
from apps.identity.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_authenticate_user_handler",
    "build_logout_handler",
    "build_refresh_token_handler",
    "build_register_user_handler",
    "build_token_service",
]


def build_token_service() -> JWTService:
    """Assemble the SimpleJWT-backed :class:`TokenService` adapter."""
    return JWTService()


def build_register_user_handler() -> RegisterUserHandler:
    """Assemble the registration use case with its adapters."""
    return RegisterUserHandler(
        users=DjangoUserRepository(),
        password_hasher=Argon2PasswordHasher(),
        password_policy=PasswordPolicy(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
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
