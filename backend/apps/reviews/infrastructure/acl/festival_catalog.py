"""ACL over the Competitions and Organization contexts.

Both adapters answer one question each and return flat values in this context's
own language (ARCH-001 §9.2): the festivals an organizer runs, and what the
organization is called. Neither hands a foreign aggregate across the boundary, so
a change to how a competition is modelled cannot reach the review page.

The catalog deliberately lists a festival in *any* state, published or not: an
organizer collecting notes at an event they have not yet published on the platform
still runs that event, and an empty picker on a banner's landing page would read
as a broken page rather than as a deliberate filter.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from apps.competitions.infrastructure.models import CompetitionModel
from apps.organization.infrastructure.models import OrganizationModel
from apps.reviews.application.interfaces import CatalogFestival

__all__ = ["DjangoFestivalCatalog", "DjangoOrganizationDirectory"]

#: How many festivals the picker offers. It is a dropdown on a phone, not an
#: archive: an organizer with more seasons than this is served by the newest ones
#: and by the note that names none of them.
_PICKER_LIMIT = 50


class DjangoFestivalCatalog:
    """Competitions ACL implementing the ``FestivalCatalog`` port."""

    def festivals_of(self, organization_id: uuid.UUID) -> Sequence[CatalogFestival]:
        """The organizer's festivals, newest first, for the optional picker."""
        rows = (
            CompetitionModel.objects.filter(organizer_id=organization_id, deleted_at__isnull=True)
            .order_by("-created_at")
            .values_list("id", "title")[:_PICKER_LIMIT]
        )
        return [CatalogFestival(id=festival_id, title=str(title or "").strip()) for festival_id, title in rows if str(title or "").strip()]

    def title_of(self, competition_id: uuid.UUID, *, organization_id: uuid.UUID) -> str | None:
        """The festival's title, or ``None`` if it is not this organizer's.

        The organization check is the point of the method. Without it, anybody
        holding a public link could file a note against a festival that belongs to
        somebody else, and the title frozen onto that note would be a name its
        owner never agreed to be associated with.
        """
        title = (
            CompetitionModel.objects.filter(pk=competition_id, organizer_id=organization_id, deleted_at__isnull=True)
            .values_list("title", flat=True)
            .first()
        )
        cleaned = str(title or "").strip()
        return cleaned or None


class DjangoOrganizationDirectory:
    """Organization ACL implementing the ``OrganizationDirectory`` port."""

    def name_of(self, organization_id: uuid.UUID) -> str | None:
        """What to call the organization on the page, or ``None`` if unknown."""
        name = OrganizationModel.objects.filter(pk=organization_id, deleted_at__isnull=True).values_list("name", flat=True).first()
        cleaned = str(name or "").strip()
        return cleaned or None
