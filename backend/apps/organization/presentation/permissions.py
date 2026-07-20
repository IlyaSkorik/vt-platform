"""Authorization for Organization staff-facing REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organization.composition import build_staff_membership_read_service
from apps.organization.domain.value_objects import StaffRole

__all__ = ["IsOrganizationAdmin", "IsOrganizationStaff"]


def _active_membership_role(request: Request) -> str | None:
    """Return the requester's active staff role, or ``None`` if not active staff."""
    user: Any = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        user_id = uuid.UUID(str(user.id))
    except (ValueError, TypeError):
        return None
    membership = build_staff_membership_read_service().active_for_user(user_id)
    return membership.role if membership is not None else None


class IsOrganizationStaff(BasePermission):
    """Grant access only to users with an active Organization staff membership."""

    message = "This endpoint is restricted to organization staff."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return _active_membership_role(request) is not None


class IsOrganizationAdmin(BasePermission):
    """Grant access only to active staff who administer the organization.

    Staff administration (inviting, revoking, changing roles) is restricted to the
    OWNER and DIRECTOR roles; every other active role may still *read* the roster.
    """

    message = "This action is restricted to organization owners and directors."

    _ADMIN_ROLES = frozenset({StaffRole.OWNER.value, StaffRole.DIRECTOR.value})

    def has_permission(self, request: Request, view: APIView) -> bool:
        return _active_membership_role(request) in self._ADMIN_ROLES
