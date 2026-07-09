"""JWT service — the concrete :class:`TokenService` adapter over SimpleJWT.

Implements the application's
:class:`~apps.identity.application.interfaces.TokenService` port using
``djangorestframework-simplejwt``. Its sole responsibility is the **token
lifecycle**: issuing an access/refresh pair for a subject, rotating a refresh
token into a new pair, and validating/decoding a presented refresh token to
extract its subject.

It holds **no repository logic and no business rules**: it never loads a ``User``,
never verifies a password, never decides whether an account may sign in (that is
the login use case's job, upstream). Blacklisting on rotation and logout is
delegated to the injected :class:`RefreshTokenStore`, keeping the persistence of
revoked tokens out of this class.
"""

from __future__ import annotations

from datetime import timedelta

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.application.dto import TokenPairDto
from apps.identity.application.exceptions import InvalidTokenError
from apps.identity.infrastructure.auth.refresh_token_store import RefreshTokenStore

__all__ = ["JWTService"]

_TOKEN_TYPE = "Bearer"


class JWTService:
    """Issue, rotate, and validate the session's JWT pair (``TokenService`` port).

    ``store`` persists blacklisted refresh tokens; ``access_token_lifetime`` is the
    access token's TTL, defaulting to SimpleJWT's configured
    ``ACCESS_TOKEN_LIFETIME`` and surfaced to clients as ``expires_in`` seconds.
    Rotation honours SimpleJWT's ``BLACKLIST_AFTER_ROTATION`` setting so a rotated
    refresh token cannot be replayed.
    """

    def __init__(
        self,
        *,
        store: RefreshTokenStore | None = None,
        access_token_lifetime: timedelta | None = None,
    ) -> None:
        self._store = store if store is not None else RefreshTokenStore()
        self._access_lifetime = access_token_lifetime if access_token_lifetime is not None else api_settings.ACCESS_TOKEN_LIFETIME

    def issue(self, *, subject: str) -> TokenPairDto:
        """Issue a fresh access + refresh pair carrying ``subject`` as the identity."""
        refresh = RefreshToken()
        refresh[api_settings.USER_ID_CLAIM] = subject
        return self._pair(refresh)

    def rotate(self, *, refresh_token: str) -> TokenPairDto:
        """Validate and invalidate ``refresh_token``, then issue a new pair.

        Raises :class:`InvalidTokenError` if the token is malformed, expired, of the
        wrong type, or already blacklisted (a replay).
        """
        old = self._decode(refresh_token)
        subject = old.get(api_settings.USER_ID_CLAIM)
        if subject is None:
            raise InvalidTokenError("Refresh token is missing its subject.")
        if api_settings.BLACKLIST_AFTER_ROTATION:
            self._store.blacklist(old)
        return self.issue(subject=str(subject))

    def revoke(self, *, refresh_token: str) -> None:
        """Validate ``refresh_token`` and blacklist it (logout).

        Raises :class:`InvalidTokenError` if the token cannot be accepted.
        """
        self._store.blacklist(self._decode(refresh_token))

    def subject_of(self, refresh_token: str) -> str:
        """Return the subject (account id) carried by a valid ``refresh_token``.

        Raises :class:`InvalidTokenError` if the token is unusable or carries no
        subject.
        """
        subject = self._decode(refresh_token).get(api_settings.USER_ID_CLAIM)
        if subject is None:
            raise InvalidTokenError("Refresh token is missing its subject.")
        return str(subject)

    def _decode(self, refresh_token: str) -> RefreshToken:
        """Decode and fully verify a refresh token, or raise :class:`InvalidTokenError`.

        SimpleJWT's ``RefreshToken`` constructor verifies the signature, expiry,
        token type, and (with the blacklist app installed) blacklist membership,
        raising ``TokenError`` for any failure — which becomes an opaque
        :class:`InvalidTokenError` so callers cannot probe token state.
        """
        try:
            # SimpleJWT's ``Token.__init__`` accepts an encoded token string at
            # runtime, though its parameter is annotated ``Token | None``.
            return RefreshToken(refresh_token)  # type: ignore[arg-type]
        except TokenError as exc:
            raise InvalidTokenError("The refresh token is invalid or expired.") from exc

    def _pair(self, refresh: RefreshToken) -> TokenPairDto:
        """Render a refresh token and its derived access token into a DTO."""
        return TokenPairDto(
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
            token_type=_TOKEN_TYPE,
            expires_in=int(self._access_lifetime.total_seconds()),
        )
