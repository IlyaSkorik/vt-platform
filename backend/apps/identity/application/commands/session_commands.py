"""Session/token command messages for the Identity & Access bounded context.

Where :mod:`apps.identity.application.commands.user_commands` carries intents that
change the ``User`` aggregate, the commands here concern the **authentication
session** — the rotating refresh-token lifecycle that lives entirely at the
credential/transport edge and never touches the aggregate. They are the input
shapes for the refresh and logout use cases (API-001 §4.5, §4.6).

Same design contract as every command: a ``frozen``, ``slots`` dataclass of
transport primitives only, fully typed, no behaviour. The raw refresh token is a
compact JWT string the presentation layer already extracted from the request body
or the httpOnly cookie; the handler hands it to the
:class:`~apps.identity.application.interfaces.TokenService` port, which validates
and rotates/revokes it. The command itself never parses or trusts it.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LogoutCommand", "RefreshTokenCommand"]


@dataclass(frozen=True, slots=True)
class RefreshTokenCommand:
    """Exchange a valid rotating refresh token for a fresh access/refresh pair.

    ``refresh_token`` is the encoded JWT the edge collected (cookie for web,
    request body for native clients). The handler delegates validation, reuse
    rejection, and rotation to the token-service port; a token that is invalid,
    expired, or already rotated surfaces as
    :class:`~apps.identity.application.exceptions.InvalidTokenError`.
    """

    refresh_token: str


@dataclass(frozen=True, slots=True)
class LogoutCommand:
    """Revoke the current session by blacklisting its refresh token.

    Logout deliberately targets only the **refresh** token: the short-lived access
    token is left to expire on its own (never invalidated server-side), while
    blacklisting the refresh token stops the session from being renewed
    (API-001 §4.6).
    """

    refresh_token: str
