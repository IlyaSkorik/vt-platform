"""Which organization a staff request is acting inside.

The platform hosts many organizations, so every staff-facing read is scoped: an
organizer sees their own organization's festivals, applications and paperwork,
and nothing of anyone else's. This module answers the two questions that scoping
turns on, for any bounded context's presentation layer.

The platform operator is the deliberate exception: they are staff of no
organization and read across all of them.
"""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.request import Request

from apps.organization.composition import build_staff_membership_read_service
from apps.platform.presentation.permissions import is_platform_administrator

__all__ = ["callers_organization_id", "is_platform_operator"]


def _user_uuid(request: Request) -> uuid.UUID | None:
    user: Any = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return uuid.UUID(str(user.id))
    except (ValueError, TypeError):
        return None


def callers_organization_id(request: Request) -> uuid.UUID | None:
    """The organization the caller is staff of, or ``None`` if they are staff of none."""
    user_id = _user_uuid(request)
    if user_id is None:
        return None
    membership = build_staff_membership_read_service().active_for_user(user_id)
    if membership is None:
        return None
    try:
        return uuid.UUID(membership.organization_id)
    except (ValueError, TypeError):  # pragma: no cover - defensive
        return None


def is_platform_operator(request: Request) -> bool:
    """Whether the caller operates the platform itself, and so is not scoped."""
    return is_platform_administrator(request)
