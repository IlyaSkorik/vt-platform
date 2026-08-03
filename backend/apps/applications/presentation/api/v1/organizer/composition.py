"""Composition root for the organizer read-model surface.

Wires the framework-free :mod:`Participant Registry port
<apps.applications.application.read_models>` to its Django adapter, and resolves
the organization's confidentiality scope (which competitions the organizer may
see participation from).
"""

from __future__ import annotations

from apps.applications.application.read_models import OrganizerParticipantRegistry
from apps.applications.infrastructure.read_models import DjangoOrganizerParticipantRegistry
from apps.competitions.infrastructure.models.competition import CompetitionModel

__all__ = [
    "build_organizer_participant_registry",
    "organization_competition_ids",
    "organization_competitions",
]


def build_organizer_participant_registry() -> OrganizerParticipantRegistry:
    """Return the organizer participant registry read model."""
    return DjangoOrganizerParticipantRegistry()


def organization_competition_ids() -> list[str]:
    """Competitions the current organizer's organization owns — the scope.

    The platform runs a single organization today, so this is every live
    competition. This is the single seam where per-organization narrowing
    plugs in once competitions carry a reliable organization key (ARCH-001
    §21.6): the registry is only ever asked about participation inside this set,
    so a child's participation in any other organization can never surface.
    """
    return [str(row["id"]) for row in CompetitionModel.objects.filter(deleted_at__isnull=True).values("id")]


def organization_competitions() -> list[dict[str, str]]:
    """The organization's competitions (id + title) for filter dropdowns."""
    return [
        {"id": str(row["id"]), "title": str(row["title"])}
        for row in CompetitionModel.objects.filter(deleted_at__isnull=True).values("id", "title").order_by("title")
    ]
