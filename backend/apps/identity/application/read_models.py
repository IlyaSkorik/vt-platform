"""The published cross-context read model of Identity user cards.

:class:`UserDirectory` is the seam other bounded contexts use to turn a bare
Identity user id into a human-facing card (email + display name) **without**
importing the ``User`` aggregate, its repository, or any value object — no
business logic leaks across the boundary (ARCH-001 §14). It mirrors, in the
opposite direction, the way Organization publishes
:class:`~apps.organization.application.read_models.OrganizationDirectory` for
Competitions to consume.

The port lives in the application layer (framework-free); its concrete
implementation is a read-side CQRS adapter assembled at the composition root.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["UserCardView", "UserDirectory"]


@dataclass(frozen=True, slots=True)
class UserCardView:
    """Published read model of a user's identity for display in another context.

    Flat and primitive-only — the *entire* contract a consumer sees when it needs
    to render "who is this user". ``display_name`` is assembled as
    given / middle / family (matching
    :attr:`~apps.identity.domain.value_objects.FullName.full`); ``status`` is a
    coarse account-lifecycle hint (``active`` once the email is verified, else
    ``registered``).
    """

    id: str
    email: str
    display_name: str
    status: str


@runtime_checkable
class UserDirectory(Protocol):
    """Port: resolve Identity user ids to their public :class:`UserCardView`.

    A batch lookup so a caller rendering many users (e.g. the staff roster)
    resolves every id in one query. Ids with no matching (non-deleted) user are
    simply absent from the returned mapping — the caller decides on a fallback
    rather than the directory inventing one.
    """

    def resolve(self, user_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, UserCardView]:
        """Return a mapping of the given ids to their user card view."""
        ...
