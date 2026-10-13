"""Which organization a staff request is acting inside.

The platform hosts many organizations, so every staff-facing read is scoped: an
organizer sees their own organization's festivals, applications and paperwork,
and nothing of anyone else's. This module answers the two questions that scoping
turns on, for any bounded context's presentation layer.

The platform operator is the deliberate exception: they are staff of no
organization and read across all of them — and, when they name one in the
``X-Acting-Organization`` header, they work *inside* it. See
:func:`acting_organization_id`.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.request import Request

from apps.organization.composition import (
    build_organization_directory,
    build_staff_membership_read_service,
)
from apps.platform.presentation.permissions import is_platform_administrator

__all__ = [
    "ACTING_ORGANIZATION_HEADER",
    "acting_organization_id",
    "callers_organization_id",
    "is_platform_operator",
]

#: The header a platform operator names the organization they are working inside.
#:
#: A header rather than a second token or a server-side "impersonation session":
#: the operator is still themselves — the same account, the same platform access,
#: revocable the same instant — and what changes is only which organization this
#: one request is about. Nothing is minted, so nothing has to be revoked, and
#: closing the tab is already the way out.
ACTING_ORGANIZATION_HEADER: Final = "X-Acting-Organization"
_ACTING_ORGANIZATION_META: Final = "HTTP_X_ACTING_ORGANIZATION"


def _user_uuid(request: Request) -> uuid.UUID | None:
    user: Any = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return uuid.UUID(str(user.id))
    except (ValueError, TypeError):
        return None


def acting_organization_id(request: Request) -> uuid.UUID | None:
    """The organization a platform operator has stepped into, or ``None``.

    Support work is done from the inside: "ваш фестиваль не пускает заявки" is
    answered by opening the organizer's own panel, with their festivals, their
    заявки and their settings, rather than by reading the database over their
    shoulder. The operator says which organization that is, and this answers
    whether they may — and whether it exists.

    Honoured **only** for an account that operates the platform. For everybody
    else the header is not refused, it is simply not read: a header anyone could
    set is a header an attacker would set first, and an endpoint that answers
    "forbidden" to it has already admitted that the header means something.

    The organization is looked up rather than trusted, so a typo in the console
    cannot scope a request to an organization that is not there — and a
    soft-deleted one is not there.
    """
    raw = str(request.META.get(_ACTING_ORGANIZATION_META) or "").strip()
    if not raw:
        return None
    if not is_platform_administrator(request):
        return None
    try:
        organization_id = uuid.UUID(raw)
    except (ValueError, TypeError):
        return None
    if not build_organization_directory().resolve([organization_id]):
        return None
    return organization_id


def callers_organization_id(request: Request) -> uuid.UUID | None:
    """The organization the caller is acting inside, or ``None`` for none.

    For staff that is the organization they belong to. For a platform operator it
    is the one they stepped into, and nothing otherwise: an operator who named no
    organization is unscoped, which is what the console itself runs on.
    """
    acting = acting_organization_id(request)
    if acting is not None:
        return acting
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
    """Whether the caller operates the platform itself, and so is not scoped.

    ``False`` while they are inside an organization. An operator who opened
    somebody's panel is *in* that panel, and "sees everything" would quietly fill
    it with other organizations' rows — which is the one thing a support visit
    must not do, because the organizer is usually looking at the same screen.
    """
    if acting_organization_id(request) is not None:
        return False
    return is_platform_administrator(request)
