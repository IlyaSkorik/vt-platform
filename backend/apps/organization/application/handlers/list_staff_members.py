from __future__ import annotations

from apps.identity.application.read_models import UserDirectory
from apps.organization.application.dto import StaffMemberView
from apps.organization.application.dto.queries import ListStaffMembersQuery
from apps.organization.application.handlers._scope import organization_of_actor
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import StaffUserId

__all__ = ["ListStaffMembersHandler"]


class ListStaffMembersHandler:
    """Use case: list every staff member of the caller's own organization.

    A read-only roster projection joining each :class:`StaffMembership` to its
    Identity user card via the published :class:`UserDirectory` port (the same
    kind of cross-context read Competitions makes against Organization). Cards
    are resolved in one batch query; a membership whose user row is absent (e.g.
    an erased account) keeps ``email`` / ``display_name`` as ``None``.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        users: UserDirectory,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._users = users

    def handle(self, query: ListStaffMembersQuery) -> list[StaffMemberView]:
        organization, _ = organization_of_actor(
            StaffUserId.from_string(query.requested_by),
            organizations=self._organizations,
            memberships=self._memberships,
        )

        memberships = self._memberships.list_by_organization(organization.id)
        cards = self._users.resolve({membership.user_id.value for membership in memberships})

        views: list[StaffMemberView] = []
        for membership in memberships:
            card = cards.get(membership.user_id.value)
            views.append(
                StaffMemberView(
                    id=membership.id.json(),
                    user_id=membership.user_id.json(),
                    email=card.email if card is not None else None,
                    display_name=card.display_name if card is not None else None,
                    role=membership.role.value,
                    status=membership.status.value,
                    invited_at=membership.invited_at,
                    accepted_at=membership.accepted_at,
                    created_at=membership.created_at,
                )
            )
        return views
