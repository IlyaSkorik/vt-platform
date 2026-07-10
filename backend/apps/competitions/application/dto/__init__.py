"""Data-transfer objects for the Competitions application layer.

Plain, serialization-agnostic input/output shapes for use cases: command DTOs
(:mod:`.commands`), query DTOs (:mod:`.queries`) and outward view projections
(:mod:`.views`). Carry only primitives so no outer layer imports the domain.
"""

from __future__ import annotations

from .views import (
    AddedChildResult,
    AdditionalServiceView,
    AdmissionRuleView,
    AgeCategoryView,
    BrandingView,
    CategoryView,
    CompetitionDetailView,
    CompetitionSummaryView,
    ContactView,
    DeadlinesView,
    DisciplineView,
    DocumentView,
    InformationBlockView,
    ParticipantGroupView,
    PeriodView,
    PricingRuleView,
    PublicationReportView,
    RegulationView,
    SettingsView,
    VenueView,
)

__all__ = [
    "AddedChildResult",
    "AdditionalServiceView",
    "AdmissionRuleView",
    "AgeCategoryView",
    "BrandingView",
    "CategoryView",
    "CompetitionDetailView",
    "CompetitionSummaryView",
    "ContactView",
    "DeadlinesView",
    "DisciplineView",
    "DocumentView",
    "InformationBlockView",
    "ParticipantGroupView",
    "PeriodView",
    "PricingRuleView",
    "PublicationReportView",
    "RegulationView",
    "SettingsView",
    "VenueView",
]
