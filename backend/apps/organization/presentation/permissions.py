"""Authorization for Organization staff-facing REST endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organization.composition import (
    build_enabled_modules_read_service,
    build_staff_membership_read_service,
)
from apps.organization.domain.value_objects import OrganizationModule, StaffRole
from apps.organization.presentation.scope import callers_organization_id
from apps.platform.presentation.permissions import is_platform_administrator

__all__ = ["IsModuleEnabled", "IsOrganizationAdmin", "IsOrganizationStaff"]


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


class IsModuleEnabled(BasePermission):
    """Grant access only while the caller's organization holds a given module.

    The real gate behind "this organizer came only for the audience vote". Composed
    with :class:`IsOrganizationStaff` rather than replacing it: being staff says the
    caller may act for an organization at all, and this says the organization bought
    the part of the platform they are pointing at.

    Used as a factory on the view, so the module travels with the endpoint::

        permission_classes = (IsAuthenticated, IsOrganizationStaff, IsModuleEnabled.of(OrganizationModule.VOTING))

    Refuses with 403 rather than 404. Which modules exist is public — it is a price
    list, not a secret — and an organizer who is told "this module is not connected"
    can act on that, where a 404 only sends them to support. The staff endpoints
    that must not confirm existence hide *rows*, which is a different question.

    The platform operator passes: they are staff of no organization and read across
    all of them (see :mod:`apps.organization.presentation.scope`), so a per-organization
    entitlement is not a question that can be asked about them.
    """

    message = "Этот модуль не подключён вашей организации."

    #: Set by :meth:`of`; the base class is never used directly.
    module: str = ""

    @classmethod
    def of(cls, module: OrganizationModule) -> type[IsModuleEnabled]:
        """Build a permission class gating on ``module``."""
        return type(
            f"IsModuleEnabled_{module.value}",
            (cls,),
            {"module": module.value},
        )

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not self.module:  # pragma: no cover - defensive: the base class gates nothing
            return False
        if is_platform_administrator(request):
            return True
        organization_id = callers_organization_id(request)
        if organization_id is None:
            return False
        return build_enabled_modules_read_service().is_enabled(
            organization_id=organization_id,
            module=self.module,
        )
