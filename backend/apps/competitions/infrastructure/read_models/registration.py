"""ORM-backed adapter for the Registration read model.

Loads the whole ``Competition`` aggregate through its repository (so every builder
rule and value object is reused verbatim) and projects it with the pure
:func:`project_registration`. Only competitions in a publicly-visible lifecycle
state resolve; drafts and archived competitions read as ``None`` (a 404 at the
edge). No business rule is re-implemented here.
"""

from __future__ import annotations

from apps.competitions.application.read_models.public_catalog import (
    PUBLIC_CATALOG_DOMAIN_STATUSES,
)
from apps.competitions.application.read_models.registration import (
    RegistrationView,
    project_registration,
)
from apps.competitions.domain.value_objects import CompetitionId
from apps.competitions.infrastructure.models import CompetitionModel
from apps.competitions.infrastructure.repositories.django_competition_repository import (
    DjangoCompetitionRepository,
)
from apps.competitions.infrastructure.system.clock import SystemClock

__all__ = ["DjangoRegistrationReader"]


class DjangoRegistrationReader:
    """Concrete registration read service over the competition aggregate."""

    def __init__(self) -> None:
        self._repository = DjangoCompetitionRepository()
        self._clock = SystemClock()

    def get(self, competition_id: str) -> RegistrationView | None:
        """Return the registration projection for ``competition_id``, or ``None``.

        Accepts a slug as readily as a uuid, matching the detail endpoint: the
        landing page and its registration block are driven by one identifier out
        of the address bar, and a projection that understood only half of them
        would leave the readable URL rendering a landing with no way to enter.
        """
        try:
            parsed: CompetitionId | None = CompetitionId.from_string(competition_id)
        except ValueError:
            parsed = self._resolve_slug(competition_id)
        if parsed is None:
            return None
        competition = self._repository.get(parsed)
        if competition is None or competition.status.value not in PUBLIC_CATALOG_DOMAIN_STATUSES:
            return None
        return project_registration(competition, now=self._clock.utcnow())

    @staticmethod
    def _resolve_slug(slug: str) -> CompetitionId | None:
        """The competition id behind a readable address, if one claims it."""
        normalized = str(slug or "").strip().lower()
        if not normalized:
            return None
        row = CompetitionModel.objects.filter(slug=normalized, deleted_at__isnull=True).values("id").first()
        return CompetitionId.from_uuid(row["id"]) if row else None
