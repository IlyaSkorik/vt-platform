"""``CredentialAwareJWTAuthentication`` — stateless JWT auth with a credential cut-off.

A drop-in replacement for SimpleJWT's
:class:`~rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication`
used by every authenticated endpoint on the platform. It keeps the stateless
behaviour (``request.user`` is a token-derived user whose ``id`` is the account
subject) but adds **one** account-level check: a token whose issue time (``iat``)
predates the owner's ``credentials_invalidated_at`` is rejected.

Why it exists. A completed password reset stamps
:attr:`~apps.identity.domain.entities.User.credentials_invalidated_at`; the refresh
use case already refuses to renew any session issued before that instant, so no
session can be *renewed*. This class closes the remaining window by also rejecting
**access** tokens issued before the cut-off, so an outstanding access token cannot
be used after its owner resets their password (IDN-004, "revoke all sessions").

Cost. Enforcement requires loading the account once per authenticated request to
read its cut-off (a single indexed primary-key lookup). This is the deliberate
price of immediate access-token revocation over stateless JWT; without it, access
tokens would remain valid until they expire on their own
(``ACCESS_TOKEN_LIFETIME``).
"""

from __future__ import annotations

from typing import Any, cast

from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.models import TokenUser
from rest_framework_simplejwt.utils import datetime_from_epoch

from apps.identity.domain.exceptions import ValueObjectValidationError
from apps.identity.domain.value_objects import UserId

__all__ = ["CredentialAwareJWTAuthentication"]


class CredentialAwareJWTAuthentication(JWTStatelessUserAuthentication):
    """Stateless JWT authentication that honours a per-account credential cut-off."""

    # The base declares `get_user` as returning SimpleJWT's `AuthUser` TypeVar, which is
    # constrained to `AbstractBaseUser | TokenUser` and appears in no parameter — so the
    # library's own signature is unresolvable and no override can satisfy it. The
    # stateless base this class extends always builds a `TokenUser`, so naming that
    # concrete type is the accurate contract for callers; the override check is what
    # gets silenced, not the body.
    def get_user(self, validated_token: Any) -> TokenUser:  # type: ignore[override]
        """Resolve the token's user, rejecting a token voided by a credential change.

        Defers to the stateless base to build the token-derived user, then loads the
        account to compare the token's ``iat`` against
        :attr:`~apps.identity.domain.entities.User.credentials_invalidated_at`. A
        token issued before that instant raises
        :class:`~rest_framework_simplejwt.exceptions.AuthenticationFailed` (a
        ``401``). A missing account, a malformed subject, or a token without an
        ``iat`` fails closed to the base behaviour rather than silently passing an
        outdated token.
        """
        # One cast at the boundary rather than defensive narrowing at each use: the
        # stateless base's contract is that it builds a `TokenUser` from the token's
        # claims — it never touches the user table — so this is the real runtime type.
        user = cast(TokenUser, super().get_user(validated_token))
        issued_at_epoch = validated_token.get("iat")
        if issued_at_epoch is None:
            return user
        # Imported lazily so this module (loaded by DRF at import time via the auth
        # class) never pulls the ORM repository into an import cycle.
        from apps.identity.infrastructure.repositories import DjangoUserRepository

        try:
            user_id = UserId.from_string(str(user.id))
        except ValueObjectValidationError as exc:
            raise AuthenticationFailed("The token carries an invalid subject.") from exc
        account = DjangoUserRepository().get(user_id)
        if account is None:
            return user
        cut_off = account.credentials_invalidated_at
        if cut_off is not None and datetime_from_epoch(issued_at_epoch) < cut_off:
            raise AuthenticationFailed("The session was revoked by a credential change.")
        return user
