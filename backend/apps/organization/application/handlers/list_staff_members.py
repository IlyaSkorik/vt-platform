from __future__ import annotations

from apps.identity.application.read_models import UserDirectory
from apps.organization.application.dto import StaffMemberView
from apps.organization.application.dto.queries import ListStaffMembersQuery
from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)

__all__ = ["ListStaffMembersHandler"]


class ListStaffMembersHandler:
    """Use case: list every staff member of the singleton organization.

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
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

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
