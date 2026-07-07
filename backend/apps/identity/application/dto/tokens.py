"""Token DTOs for the Identity & Access application layer.

The output shape of the session use cases: an issued or rotated pair of JWTs plus
the metadata a client needs to use them. Like every other DTO here it is a flat,
``frozen``, serialization-agnostic dataclass of primitives — the presentation
edge reads it without importing the token library, and the application layer
never touches an HTTP cookie or header.

``expires_in`` describes the **access** token's remaining lifetime in whole
seconds (API-000 §17, API-001 §4.4); ``token_type`` is the ``Authorization``
scheme (always ``"Bearer"``). The ``refresh_token`` travels out so the edge can
place it in an httpOnly cookie (web) or the response body (native clients).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["TokenPairDto"]


@dataclass(frozen=True, slots=True)
class TokenPairDto:
    """An issued/rotated access + refresh token pair with client metadata."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
