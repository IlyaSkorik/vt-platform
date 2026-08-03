"""Which competitions a staff caller may see and touch.

A competition belongs to the organization that runs it (``organizer_id``). With
several organizations connected to the platform, that stops being a label and
becomes the boundary: an organizer works inside their own organization's
festivals and nowhere else.

Who the caller is scoped to is the Organization context's answer, taken from its
presentation-level helper; what follows from it for a competition is here.
"""

from __future__ import annotations

import uuid

from rest_framework.request import Request

from apps.organization.presentation.scope import (
    callers_organization_id,
    is_platform_operator,
)

__all__ = ["callers_organization_id", "is_platform_operator", "may_reach_competition"]


def may_reach_competition(request: Request, organizer_id: uuid.UUID | None) -> bool:
    """Whether this caller may read or edit a competition owned by ``organizer_id``."""
    if is_platform_operator(request):
        return True
    callers = callers_organization_id(request)
    return callers is not None and organizer_id is not None and callers == organizer_id
