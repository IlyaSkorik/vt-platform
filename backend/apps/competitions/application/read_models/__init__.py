"""Read-side (CQRS) projections for the Competitions bounded context.

These are deliberately *separate* from the organizer write API and the
:class:`~apps.competitions.domain.entities.Competition` aggregate. A projection
answers a read question over the persisted rows without rehydrating the
aggregate or touching its invariants (ARCH-001 §7.2, §14).
"""

from __future__ import annotations

from apps.competitions.application.read_models.public_catalog import (
    PUBLIC_CATALOG_DOMAIN_STATUSES,
    ParticipationMode,
    PublicCatalogReadService,
    PublicFestivalContactsView,
    PublicFestivalDetailView,
    PublicFestivalEmergencyView,
    PublicFestivalFaqItemView,
    PublicFestivalFormatView,
    PublicFestivalGalleryImageView,
    PublicFestivalJuryCardView,
    PublicFestivalLandingBlockView,
    PublicFestivalLandingView,
    PublicFestivalPartnerCardView,
    PublicFestivalPricingView,
    PublicFestivalRegulationView,
    PublicFestivalSocialLinksView,
    PublicFestivalTeamMemberView,
    PublicFestivalVenueView,
    PublicFestivalView,
    aggregate_pricing,
    classify_participation_mode,
    project_contacts,
    project_landing,
    public_status_for,
    resolve_city,
    resolve_cover_image,
)

__all__ = [
    "PUBLIC_CATALOG_DOMAIN_STATUSES",
    "ParticipationMode",
    "PublicCatalogReadService",
    "PublicFestivalContactsView",
    "PublicFestivalDetailView",
    "PublicFestivalEmergencyView",
    "PublicFestivalFaqItemView",
    "PublicFestivalFormatView",
    "PublicFestivalGalleryImageView",
    "PublicFestivalJuryCardView",
    "PublicFestivalLandingBlockView",
    "PublicFestivalLandingView",
    "PublicFestivalPartnerCardView",
    "PublicFestivalPricingView",
    "PublicFestivalRegulationView",
    "PublicFestivalSocialLinksView",
    "PublicFestivalTeamMemberView",
    "PublicFestivalVenueView",
    "PublicFestivalView",
    "aggregate_pricing",
    "classify_participation_mode",
    "project_contacts",
    "project_landing",
    "public_status_for",
    "resolve_city",
    "resolve_cover_image",
]
