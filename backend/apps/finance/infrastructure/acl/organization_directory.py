"""ACL over the Organization context.

One question, one flat answer in this context's own language (ARCH-001 §9.2):
what the connected organizations are called. No foreign aggregate crosses the
boundary, so how an organization is modelled cannot reach the expense book.

The whole map is fetched at once rather than a name at a time. The ledger is a
table of costs across every client, so resolving the name per row would be one
query per row for a list that is at most a few dozen organizations wide.
"""

from __future__ import annotations

import uuid

from apps.organization.infrastructure.models import OrganizationModel

__all__ = ["DjangoOrganizationDirectory"]


class DjangoOrganizationDirectory:
    """Organization ACL implementing the ``OrganizationDirectory`` port."""

    def names(self) -> dict[uuid.UUID, str]:
        """Every connected organization's name, by id."""
        rows = OrganizationModel.objects.filter(deleted_at__isnull=True).values_list("id", "name")
        return {organization_id: str(name) for organization_id, name in rows}
