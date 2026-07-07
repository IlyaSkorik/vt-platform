"""Authentication adapters for the Identity & Access bounded context.

Concrete infrastructure implementations of the credential/session ports declared
in :mod:`apps.identity.application.interfaces`:

* :class:`Argon2PasswordHasher` — the ``PasswordHasher`` port over ``argon2-cffi``.
* :class:`JWTService`           — the ``TokenService`` port over SimpleJWT.
* :class:`RefreshTokenStore`    — refresh-token blacklist over SimpleJWT's tables.

These depend inward on the application ports and the domain value objects; nothing
in the application or domain layers depends on this package (ARCH-001 §7.2).
"""

from __future__ import annotations

from apps.identity.infrastructure.auth.jwt_service import JWTService
from apps.identity.infrastructure.auth.password_hasher import Argon2PasswordHasher
from apps.identity.infrastructure.auth.refresh_token_store import RefreshTokenStore

__all__ = ["Argon2PasswordHasher", "JWTService", "RefreshTokenStore"]
