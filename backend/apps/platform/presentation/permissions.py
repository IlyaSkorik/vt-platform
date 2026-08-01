"""Authorization for the platform operator's own endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.platform.composition import build_platform_access_read_service

__all__ = ["IsPlatformAdministrator", "is_platform_administrator"]


def is_platform_administrator(request: Request) -> bool:
    """Whether the request is made by an account holding platform-operator access.

    Also used outside the permission class: staff endpoints scope their reads to
    the caller's own organization, and the platform operator is the one caller for
    whom that scope is "everything".
    """
    user: Any = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    try:
        user_id = uuid.UUID(str(user.id))
    except (ValueError, TypeError):
        return False
    return build_platform_access_read_service().is_platform_administrator(user_id)


class IsPlatformAdministrator(BasePermission):
    """Grant access only to accounts holding platform-operator access.

    Deliberately independent of staff roles: an organization's OWNER is the top of
    that organization and gets nothing here, and nothing inside an organization can
    promote anyone to this level.
    """

    message = "This endpoint is restricted to platform administrators."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_platform_administrator(request)
