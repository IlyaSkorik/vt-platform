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

from django.utils import timezone

from apps.competitions.application.read_models.public_catalog import (
    PUBLIC_CATALOG_DOMAIN_STATUSES,
    OrganizerContactFacts,
    PublicFestivalDetailView,
    PublicFestivalDocumentView,
    PublicFestivalFormatView,
    PublicFestivalLandingBlockView,
    PublicFestivalLandingView,
    PublicFestivalOrganizerView,
    PublicFestivalPricingView,
    PublicFestivalRegulationView,
    PublicFestivalView,
    aggregate_pricing,
    classify_participation_mode,
    is_public_document_visibility,
    project_contacts,
    project_landing,
    public_status_for,
    resolve_city,
    resolve_landing_cover,
    resolve_poster_image,
)
from apps.competitions.domain.landing_configuration import (
    SYSTEM_BLOCK_DOCUMENTS_ID,
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
        organizers = self._resolve_organizers(organizer_ids)

        return [self._project(competition, organizers) for competition in competitions]

    def get_festival(self, festival_id: str) -> PublicFestivalDetailView | None:
        visible = CompetitionModel.objects.filter(
            status__in=PUBLIC_CATALOG_DOMAIN_STATUSES,
            deleted_at__isnull=True,
        ).prefetch_related("participation_formats", "pricing_rules", "categories", "documents")

        # A slug *or* a uuid: the readable address is what the site links and what
        # search indexes, while every uuid link already handed out — an emailed
        # one, a printed one — has to keep resolving. Which form arrived is told
        # apart by parsing, not by asking the caller.
        try:
            pk = uuid.UUID(str(festival_id))
        except (ValueError, TypeError, AttributeError):
            slug = str(festival_id or "").strip().lower()
            # An empty or malformed segment can never match a real competition;
            # a miss rather than a 500 on hostile or typo'd input.
            competition = visible.filter(slug=slug).first() if slug else None
        else:
            competition = visible.filter(id=pk).first()

        if competition is None:
            return None

        organizers = self._resolve_organizers({competition.organizer_id})
        return self._project_detail(competition, organizers)

    def _resolve_organizers(
        self,
        organizer_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, OrganizerCardView]:
        """Resolve organizer cards, backfilling misses with the singleton org.

        A competition's ``organizer_id`` is a free-form, client-supplied grouping
        id that is not guaranteed to point at the (singleton) organization row, so
        the batch lookup frequently misses. The platform runs a single
        organization that is the source of truth for the public organizer identity
        and contacts, so any unresolved id falls back to it — the fixed
        ``_FALLBACK_ORGANIZER_NAME`` is used only when no organization exists yet.
        """
        organizers = self._directory.resolve(organizer_ids)
        missing = organizer_ids - organizers.keys()
        if missing:
            default = self._directory.default_organizer()
            if default is not None:
                for organizer_id in missing:
                    organizers[organizer_id] = default
        return organizers

    def _project(
        self,
        competition: CompetitionModel,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalView:
        formats = self._formats(competition)

        # PUBLIC_CATALOG_DOMAIN_STATUSES gates the query, so this is never None.
        has_open, has_upcoming = self._registration_flags(competition)
        public_status = public_status_for(
            competition.status,
            has_open_nomination=has_open,
            has_upcoming_nomination=has_upcoming,
        )
        assert public_status is not None

        return PublicFestivalView(
            id=str(competition.id),
            slug=competition.slug,
            title=competition.title,
            season=competition.season,
            description=competition.description,
            status=public_status,
            organizer=self._organizer_view(competition.organizer_id, organizers),
            city=resolve_city(competition.contacts_config),
            venue_name=competition.venue_name,
            venue_address=competition.venue_address,
            # Catalog card → the festival poster ("Афиша"), never the hero cover.
            cover_image=resolve_poster_image(competition.poster, competition.banner),
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

        has_open, has_upcoming = self._registration_flags(competition)
        public_status = public_status_for(
            competition.status,
            has_open_nomination=has_open,
            has_upcoming_nomination=has_upcoming,
        )
        assert public_status is not None

        config = landing_config_from_json(competition.landing_config)
        regulation = self._regulation(competition)
        documents = self._documents(competition)
        landing = self._landing_with_markers(project_landing(config), config, regulation, documents)
        contacts = project_contacts(
            contacts_config_from_json(competition.contacts_config),
            organizer=self._organizer_contact_facts(competition.organizer_id, organizer, organizers),
            venue_name=competition.venue_name,
            venue_address=competition.venue_address,
        )

        return PublicFestivalDetailView(
            id=str(competition.id),
            slug=competition.slug,
            title=competition.title,
            season=competition.season,
            description=competition.description,
            status=public_status,
            organizer=organizer,
            city=resolve_city(competition.contacts_config),
            venue_name=competition.venue_name,
            venue_address=competition.venue_address,
            # Landing hero → the HERO block cover ("Обложка"), never the poster.
            cover_image=resolve_landing_cover(competition.landing_config),
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
            documents=tuple(documents),
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    @classmethod
    def _landing_with_markers(
        cls,
        landing: PublicFestivalLandingView,
        config: LandingConfiguration,
        regulation: PublicFestivalRegulationView | None,
        documents: list[PublicFestivalDocumentView],
    ) -> PublicFestivalLandingView:
        """Guarantee REGULATION / DOCUMENTS markers for configs that predate them.

        The organizer controls both blocks like any other (enable / disable /
        reorder). But competitions whose landing config was persisted before the
        block types existed have none, so their regulation / public documents
        would silently vanish. When such content exists yet no matching block is
        configured at all, prepend a synthetic enabled marker — matching the old
        top-of-page placement — without touching organizer-authored configs.
        """
        blocks = list(landing.blocks)
        # Prepend in reverse priority so the final order is REGULATION, DOCUMENTS, …
        if documents and not cls._has_block(config, LandingBlockType.DOCUMENTS):
            blocks.insert(0, cls._marker(SYSTEM_BLOCK_DOCUMENTS_ID, LandingBlockType.DOCUMENTS))
        if regulation is not None and not cls._has_block(config, LandingBlockType.REGULATION):
            blocks.insert(0, cls._marker(SYSTEM_BLOCK_REGULATION_ID, LandingBlockType.REGULATION))
        return PublicFestivalLandingView(blocks=tuple(blocks))

    @staticmethod
    def _has_block(config: LandingConfiguration, block_type: LandingBlockType) -> bool:
        return any(block.type is block_type for block in config.blocks)

    @staticmethod
    def _marker(block_id: str, block_type: LandingBlockType) -> PublicFestivalLandingBlockView:
        return PublicFestivalLandingBlockView(
            id=block_id,
            type=block_type.value,
            sort_order=0,
            title=None,
            subtitle=None,
            cover_image=None,
            body=None,
            content_format=None,
        )

    @staticmethod
    def _documents(competition: CompetitionModel) -> list[PublicFestivalDocumentView]:
        published_public = [
            document
            for document in competition.documents.all()
            if document.published and is_public_document_visibility(document.visibility)
        ]
        published_public.sort(key=lambda document: (document.sort_order, document.title))
        return [
            PublicFestivalDocumentView(
                id=str(document.id),
                title=document.title,
                category=document.category,
                description=document.description,
                file_reference=document.file_reference,
            )
            for document in published_public
        ]

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
    def _registration_flags(competition: CompetitionModel) -> tuple[bool, bool]:
        """Whether any nomination is open now, and whether any is scheduled to open later.

        Registration is per nomination (each with its own window + early-stop flag);
        these two flags let :func:`public_status_for` refine a PUBLISHED competition's
        public status into accepting / coming-soon / registration-closed.
        """
        now = timezone.now()
        has_open = False
        has_upcoming = False
        for category in competition.categories.all():
            if category.registration_stopped:
                continue
            opens_at = category.registration_opens_at
            closes_at = category.registration_closes_at
            if opens_at is None and closes_at is None:
                continue  # unconfigured window — neither open nor upcoming
            if opens_at is not None and now < opens_at:
                has_upcoming = True
                continue
            if closes_at is not None and now > closes_at:
                continue  # window already passed
            has_open = True
        return has_open, has_upcoming

    @staticmethod
    def _organizer_view(
        organizer_id: uuid.UUID,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> PublicFestivalOrganizerView:
        card = organizers.get(organizer_id)
        if card is None:
            return PublicFestivalOrganizerView(id=str(organizer_id), name=_FALLBACK_ORGANIZER_NAME, logo=None)
        return PublicFestivalOrganizerView(id=card.id, name=card.name, logo=card.logo)

    @staticmethod
    def _organizer_contact_facts(
        organizer_id: uuid.UUID,
        organizer: PublicFestivalOrganizerView,
        organizers: dict[uuid.UUID, OrganizerCardView],
    ) -> OrganizerContactFacts:
        """Map the organizer card into the contact facts the projection consumes.

        ``name`` reuses the already-resolved organizer view (carrying the
        ``_FALLBACK_ORGANIZER_NAME`` fallback); the channels come from the card
        when the organization was resolved, and are all ``None`` otherwise.
        """
        card = organizers.get(organizer_id)
        if card is None:
            return OrganizerContactFacts(name=organizer.name)
        return OrganizerContactFacts(
            name=organizer.name,
            phone=card.phone,
            email=card.email,
            website=card.website,
            address=card.address,
            vk=card.vk,
            instagram=card.instagram,
            telegram=card.telegram,
            legal_information=card.legal_information,
        )
