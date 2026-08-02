"""Shared user-resource projection for the Identity REST API v1.

The single place the ``user`` wire resource (API-001 §4.1) is built from a
:class:`~apps.identity.application.dto.UserDto`. Both the authentication edge
(registration, email-verification responses) and the cross-context ``/users/me``
composition edge render the *same* shape from here, so the user's public
representation has one definition and cannot drift between endpoints.

Framework-light: builds plain ``dict`` bodies from a DTO. It holds the mapping
from the account's lifecycle flags to the API ``status`` string and nothing else.
"""

from __future__ import annotations

from typing import Any

from apps.identity.application.dto import UserDto

__all__ = ["user_resource", "user_status"]


def user_status(user: UserDto) -> str:
    """Derive the API ``status`` string from the account's lifecycle flags."""
    if user.is_deleted:
        return "deleted"
    if user.is_locked:
        return "suspended"
    if user.is_email_verified:
        return "active"
    return "registered"


def user_resource(user: UserDto) -> dict[str, Any]:
    """Project a :class:`UserDto` into the full user resource (API-001 §4.1)."""
    return {
        "id": user.id,
        "type": "user",
        "email": user.email,
        "displayName": user.full_name,
        "status": user_status(user),
        "emailVerified": user.is_email_verified,
        # The number itself, not just whether it is verified: this resource is only
        # ever the caller's own account, and a settings screen cannot offer to
        # change a value it is unable to show.
        "phone": user.phone,
        "phoneVerified": user.is_phone_verified,
        "mfaEnabled": False,
        "locale": user.locale,
        "createdAt": user.created_at.isoformat().replace("+00:00", "Z"),
        "updatedAt": user.updated_at.isoformat().replace("+00:00", "Z"),
    }
