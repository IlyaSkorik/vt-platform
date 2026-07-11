"""Authorization for Organization staff-facing REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organization.composition import build_staff_membership_read_service

__all__ = ["IsOrganizationStaff"]


class IsOrganizationStaff(BasePermission):
    """Grant access only to users with an active Organization staff membership."""

    message = "This endpoint is restricted to organization staff."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user: Any = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        try:
            user_id = uuid.UUID(str(user.id))
        except (ValueError, TypeError):
            return False
        return build_staff_membership_read_service().active_for_user(user_id) is not None
