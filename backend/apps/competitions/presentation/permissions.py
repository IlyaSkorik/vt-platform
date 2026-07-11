"""Authorization for the Competitions REST edge.

Organizer endpoints are staff-only (ARCH-001 §14): the *source of truth* for
"is this user staff?" is the Organization bounded context, consulted through its
published :class:`~apps.organization.application.read_models.StaffMembershipReadService`
read-port. This module is only a thin DRF adapter over that port — it re-implements
no role logic, so authorization stays in one place.
"""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organization.composition import build_staff_membership_read_service

__all__ = ["IsOrganizationStaff"]


class IsOrganizationStaff(BasePermission):
    """Grant access only to users with an active Organization staff membership.

    Participants (and any other authenticated non-staff user) are denied. Absence
    of an active membership — the common case — is a plain deny, never an error.
    """

    message = "Organizer endpoints are restricted to organization staff."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user: Any = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        try:
            user_id = uuid.UUID(str(user.id))
        except (ValueError, TypeError):
            return False
        return build_staff_membership_read_service().active_for_user(user_id) is not None
