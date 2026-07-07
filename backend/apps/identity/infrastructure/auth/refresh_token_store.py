"""Refresh-token blacklist store — SimpleJWT blacklist adapter.

A thin persistence helper over ``djangorestframework-simplejwt``'s **own**
blacklist tables (:class:`OutstandingToken` / :class:`BlacklistedToken`). It does
not invent a blacklist: it writes exactly the rows SimpleJWT's own
``RefreshToken.check_blacklist`` reads, so a token this store blacklists is
rejected on its next presentation (rotation reuse, or after logout).

Why not simply call ``RefreshToken.blacklist()``? That helper resolves the token's
subject through ``get_user_model()`` — but this platform's identity is the custom
``User`` aggregate, not ``django.contrib.auth``'s user, so a UUID-v7 subject would
fail that lookup. We therefore persist the blacklist rows directly (with a null
user, which the model permits), keeping the mechanism SimpleJWT's while decoupling
it from Django's auth user. This is a persistence adapter only — no token
validation, issuance, or business logic lives here.
"""

from __future__ import annotations

from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch

__all__ = ["RefreshTokenStore"]


class RefreshTokenStore:
    """Blacklist and membership checks over SimpleJWT's blacklist tables."""

    def blacklist(self, token: RefreshToken) -> None:
        """Add ``token`` to the blacklist (idempotent).

        Ensures an :class:`OutstandingToken` row exists for the token's ``jti`` and
        marks it blacklisted. Repeated calls are safe: both writes are
        ``get_or_create``.
        """
        jti = str(token[api_settings.JTI_CLAIM])
        expires_at = datetime_from_epoch(token["exp"])
        outstanding, _ = OutstandingToken.objects.get_or_create(
            jti=jti,
            defaults={
                "token": str(token),
                "created_at": token.current_time,
                "expires_at": expires_at,
                "user": None,
            },
        )
        BlacklistedToken.objects.get_or_create(token=outstanding)

    def is_blacklisted(self, token: RefreshToken) -> bool:
        """Whether ``token`` (by ``jti``) is currently blacklisted."""
        jti = str(token[api_settings.JTI_CLAIM])
        return BlacklistedToken.objects.filter(token__jti=jti).exists()
