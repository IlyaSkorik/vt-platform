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
    PublicFestivalDetailView,
    PublicFestivalFormatView,
    PublicFestivalLandingBlockView,
    PublicFestivalLandingView,
    PublicFestivalOrganizerView,
    PublicFestivalPricingView,
    PublicFestivalRegulationView,
    PublicFestivalView,
    aggregate_pricing,
    classify_participation_mode,
    project_contacts,
    project_landing,
    public_status_for,
    resolve_city,
    resolve_cover_image,
)
from apps.competitions.domain.landing_configuration import (
    SYSTEM_BLOCK_REGULATION_ID,
    LandingBlockType,
    LandingConfiguration,
)
from apps.competitions.infrastructure.mappers.contacts_config_json import contacts_config_from_json
from apps.competitions.infrastructure.mappers.landing_config_json import landing_config_from_json
from apps.competitions.infrastructure.models import CompetitionModel, RegulationModel
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

    def get_festival(self, festival_id: str) -> PublicFestivalDetailView | None:
        try:
            pk = uuid.UUID(str(festival_id))
        except (ValueError, TypeError, AttributeError):
            # A malformed id can never match a real competition — treat it as a
            # miss rather than surfacing a 500 on hostile/typo'd input.
            return None

        competition = (
            CompetitionModel.objects.filter(
                id=pk,
                status__in=PUBLIC_CATALOG_DOMAIN_STATUSES,
                deleted_at__isnull=True,
            )
            .prefetch_related("participation_formats", "pricing_rules", "categories")
            .first()
        )
        if competition is None:
            return None

        organizers = self._directory.resolve({competition.organizer_id})
        return self._project_detail(competition, organizers)

    def _project(
        self,
        competition: CompetitionModel,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalView:
        formats = self._formats(competition)

        # PUBLIC_CATALOG_DOMAIN_STATUSES gates the query, so this is never None.
        public_status = public_status_for(competition.status)
        assert public_status is not None

        return PublicFestivalView(
            id=str(competition.id),
            title=competition.title,
            season=competition.season,
            description=competition.description,
            status=public_status,
            organizer=self._organizer_view(competition.organizer_id, organizers),
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
            pricing=self._pricing(competition),
            formats=formats,
            modes=self._modes(formats),
            categories=self._categories(competition),
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    def _project_detail(
        self,
        competition: CompetitionModel,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalDetailView:
        formats = self._formats(competition)
        organizer = self._organizer_view(competition.organizer_id, organizers)

        public_status = public_status_for(competition.status)
        assert public_status is not None

        config = landing_config_from_json(competition.landing_config)
        regulation = self._regulation(competition)
        landing = self._landing_with_regulation(project_landing(config), config, regulation)
        contacts = project_contacts(
            contacts_config_from_json(competition.contacts_config),
            organizer_name=organizer.name,
            venue_name=competition.venue_name,
            venue_address=competition.venue_address,
        )

        return PublicFestivalDetailView(
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
            pricing=self._pricing(competition),
            formats=tuple(formats),
            modes=tuple(self._modes(formats)),
            categories=tuple(self._categories(competition)),
            landing=landing,
            contacts=contacts,
            regulation=regulation,
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    @staticmethod
    def _landing_with_regulation(
        landing: PublicFestivalLandingView,
        config: LandingConfiguration,
        regulation: PublicFestivalRegulationView | None,
    ) -> PublicFestivalLandingView:
        """Guarantee a REGULATION marker for configs that predate the block type.

        The organizer controls the regulation block like any other (enable /
        disable / reorder). But competitions whose landing config was persisted
        before REGULATION existed have no such block, so their regulation would
        silently vanish. When a regulation exists yet no REGULATION block is
        configured at all, prepend a synthetic enabled marker — matching the old
        top-of-page placement — without touching organizer-authored configs.
        """
        if regulation is None:
            return landing
        if any(block.type is LandingBlockType.REGULATION for block in config.blocks):
            return landing
        marker = PublicFestivalLandingBlockView(
            id=SYSTEM_BLOCK_REGULATION_ID,
            type=LandingBlockType.REGULATION.value,
            sort_order=0,
            title=None,
            subtitle=None,
            cover_image=None,
            body=None,
            content_format=None,
        )
        return PublicFestivalLandingView(blocks=(marker, *landing.blocks))

    @staticmethod
    def _regulation(competition: CompetitionModel) -> PublicFestivalRegulationView | None:
        """Resolve the competition's current regulation ("Положение фестиваля").

        Only the version the aggregate marks current (``current_regulation_id``)
        is exposed; superseded versions never surface publicly. Returns ``None``
        when no regulation is set or the pointer dangles.
        """
        regulation_id = competition.current_regulation_id
        if regulation_id is None:
            return None
        regulation = RegulationModel.objects.filter(
            id=regulation_id, competition_id=competition.id
        ).first()
        if regulation is None:
            return None
        return PublicFestivalRegulationView(
            title=regulation.title,
            version=regulation.document_version,
            publication_date=regulation.publication_date,
            file_reference=regulation.file_reference,
        )

    @staticmethod
    def _formats(competition: CompetitionModel) -> list[PublicFestivalFormatView]:
        enabled_formats = sorted(
            (fmt for fmt in competition.participation_formats.all() if fmt.enabled),
            key=lambda fmt: (fmt.sort_order, fmt.name),
        )
        return [
            PublicFestivalFormatView(
                name=fmt.name,
                mode=(mode.value if (mode := classify_participation_mode(fmt.name)) else None),
            )
            for fmt in enabled_formats
        ]

    @staticmethod
    def _modes(formats: list[PublicFestivalFormatView]) -> list[str]:
        return sorted({fmt.mode for fmt in formats if fmt.mode is not None})

    @staticmethod
    def _pricing(competition: CompetitionModel) -> PublicFestivalPricingView:
        return aggregate_pricing([(rule.amount, rule.currency) for rule in competition.pricing_rules.all()])

    @staticmethod
    def _categories(competition: CompetitionModel) -> list[str]:
        return [
            category.name
            for category in sorted(
                competition.categories.all(),
                key=lambda category: (category.sort_order, category.name),
            )
        ]

    @staticmethod
    def _organizer_view(
        organizer_id: uuid.UUID,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalOrganizerView:
        card = organizers.get(organizer_id)
        if card is None:
            return PublicFestivalOrganizerView(id=str(organizer_id), name=_FALLBACK_ORGANIZER_NAME, logo=None)
        return PublicFestivalOrganizerView(id=card.id, name=card.name, logo=card.logo)
