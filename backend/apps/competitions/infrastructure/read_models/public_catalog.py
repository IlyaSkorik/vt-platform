"""ORM-backed adapter for the Public Festival Catalog read model.

Concrete :class:`PublicCatalogReadService` (structural — no inheritance). One
indexed query over ``competitions_competition`` (filtered to the public
lifecycle states, newest first) with the display-relevant children prefetched,
then each row is projected in Python using the pure rules from the application
layer. Organizer identities are resolved in a single batch through the
Organization context's published :class:`OrganizationDirectory` read-port, so no
Organization aggregate or model leaks across the boundary (ARCH-001 §14).
"""

from __future__ import annotations

import uuid

from apps.competitions.application.read_models.public_catalog import (
    PUBLIC_CATALOG_DOMAIN_STATUSES,
    PublicFestivalFormatView,
    PublicFestivalOrganizerView,
    PublicFestivalView,
    aggregate_pricing,
    classify_participation_mode,
    public_status_for,
    resolve_city,
    resolve_cover_image,
)
from apps.competitions.infrastructure.models import CompetitionModel
from apps.organization.application.read_models import OrganizationDirectory, OrganizerCardView

__all__ = ["DjangoPublicCatalogReader"]

_FALLBACK_ORGANIZER_NAME = "Организатор"


class DjangoPublicCatalogReader:
    """Concrete public-catalog read service over the competition tables."""

    def __init__(self, *, directory: OrganizationDirectory) -> None:
        self._directory = directory

    def list_festivals(self) -> list[PublicFestivalView]:
        competitions = list(
            CompetitionModel.objects.filter(
                status__in=PUBLIC_CATALOG_DOMAIN_STATUSES,
                deleted_at__isnull=True,
            )
            .prefetch_related("participation_formats", "pricing_rules", "categories")
            .order_by("-created_at", "-id")
        )

        organizer_ids = {competition.organizer_id for competition in competitions}
        organizers = self._directory.resolve(organizer_ids)

        return [self._project(competition, organizers) for competition in competitions]

    def _project(
        self,
        competition: CompetitionModel,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalView:
        enabled_formats = sorted(
            (fmt for fmt in competition.participation_formats.all() if fmt.enabled),
            key=lambda fmt: (fmt.sort_order, fmt.name),
        )
        formats = [
            PublicFestivalFormatView(
                name=fmt.name,
                mode=(mode.value if (mode := classify_participation_mode(fmt.name)) else None),
            )
            for fmt in enabled_formats
        ]
        modes = sorted({fmt.mode for fmt in formats if fmt.mode is not None})

        pricing = aggregate_pricing(
            [(rule.amount, rule.currency) for rule in competition.pricing_rules.all()]
        )

        categories = [
            category.name
            for category in sorted(
                competition.categories.all(), key=lambda category: (category.sort_order, category.name)
            )
        ]

        organizer = self._organizer_view(competition.organizer_id, organizers)

        # PUBLIC_CATALOG_DOMAIN_STATUSES gates the query, so this is never None.
        public_status = public_status_for(competition.status)
        assert public_status is not None

        return PublicFestivalView(
            id=str(competition.id),
            title=competition.title,
            season=competition.season,
            description=competition.description,
            status=public_status,
            organizer=organizer,
            city=resolve_city(competition.contacts_config),
            venue_name=competition.venue_name,
            venue_address=competition.venue_address,
            cover_image=resolve_cover_image(
                competition.landing_config,
                poster=competition.poster,
                banner=competition.banner,
            ),
            competition_start=competition.competition_start,
            competition_end=competition.competition_end,
            registration_start=competition.registration_start,
            registration_end=competition.registration_end,
            application_deadline=competition.deadline_application,
            pricing=pricing,
            formats=formats,
            modes=modes,
            categories=categories,
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    @staticmethod
    def _organizer_view(
        organizer_id: uuid.UUID,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalOrganizerView:
        card = organizers.get(organizer_id)
        if card is None:
            return PublicFestivalOrganizerView(
                id=str(organizer_id), name=_FALLBACK_ORGANIZER_NAME, logo=None
            )
        return PublicFestivalOrganizerView(id=card.id, name=card.name, logo=card.logo)
