"""Session command handlers (use cases) for the Identity & Access context.

The refresh and logout use cases (API-001 §4.5, §4.6). Both are thin orchestrators
over the :class:`~apps.identity.application.interfaces.TokenService` port: unlike
the ``User``-aggregate handlers they load no aggregate, touch no repository, and
emit no domain events, because the rotating refresh-token lifecycle lives wholly
at the credential/transport edge and never changes account state (this mirrors
:class:`~apps.identity.application.handlers.user_handlers.AuthenticateUserHandler`,
which likewise leaves token issuance to the edge).

They exist as first-class handlers so the presentation layer keeps a uniform
shape — every request flows serializer → command → handler → DTO — and so the
token port stays the single seam a test or a future transport swaps out. Error
translation is trivial here: the port already speaks the application vocabulary
(:class:`~apps.identity.application.exceptions.InvalidTokenError`), so no
``translate_domain_errors`` wrapper is needed.

This module imports nothing from infrastructure, presentation, or Django.
"""

from __future__ import annotations

from apps.identity.application.commands import LogoutCommand, RefreshTokenCommand
from apps.identity.application.dto import TokenPairDto
from apps.identity.application.interfaces import TokenService

__all__ = ["LogoutHandler", "RefreshTokenHandler"]


class RefreshTokenHandler:
    """Use case: rotate a refresh token into a fresh access + refresh pair.

    Delegates validation, reuse rejection, and rotation to the
    :class:`TokenService`; a token that is invalid, expired, of the wrong type, or
    already rotated surfaces as
    :class:`~apps.identity.application.exceptions.InvalidTokenError` (mapped to
    ``401`` at the edge). On success the presented token is invalidated, so it
    cannot be replayed.
    """

    def __init__(self, *, tokens: TokenService) -> None:
        self._tokens = tokens

    def handle(self, command: RefreshTokenCommand) -> TokenPairDto:
        return self._tokens.rotate(refresh_token=command.refresh_token)


class LogoutHandler:
    """Use case: revoke the current session by blacklisting its refresh token.

    Only the refresh token is revoked; the short-lived access token is left to
    expire naturally (API-001 §4.6). Presenting a token the service cannot accept
    raises :class:`~apps.identity.application.exceptions.InvalidTokenError`.
    """

    def __init__(self, *, tokens: TokenService) -> None:
        self._tokens = tokens

    def handle(self, command: LogoutCommand) -> None:
        self._tokens.revoke(refresh_token=command.refresh_token)
