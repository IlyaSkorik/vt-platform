"""ORM-backed adapter for the Registration read model.

Loads the whole ``Competition`` aggregate through its repository (so every builder
rule and value object is reused verbatim) and projects it with the pure
:func:`project_registration`. Only competitions in a publicly-visible lifecycle
state resolve; drafts and archived competitions read as ``None`` (a 404 at the
edge). No business rule is re-implemented here.
"""

from __future__ import annotations

from apps.competitions.application.read_models.public_catalog import PUBLIC_CATALOG_DOMAIN_STATUSES
from apps.competitions.application.read_models.registration import RegistrationView, project_registration
from apps.competitions.domain.value_objects import CompetitionId
from apps.competitions.infrastructure.repositories.django_competition_repository import DjangoCompetitionRepository
from apps.competitions.infrastructure.system.clock import SystemClock

__all__ = ["DjangoRegistrationReader"]


class DjangoRegistrationReader:
    """Concrete registration read service over the competition aggregate."""

    def __init__(self) -> None:
        self._repository = DjangoCompetitionRepository()
        self._clock = SystemClock()

    def get(self, competition_id: str) -> RegistrationView | None:
        """Return the registration projection for ``competition_id``, or ``None``."""
        try:
            parsed = CompetitionId.from_string(competition_id)
        except ValueError:
            return None
        competition = self._repository.get(parsed)
        if competition is None or competition.status.value not in PUBLIC_CATALOG_DOMAIN_STATUSES:
            return None
        return project_registration(competition, now=self._clock.utcnow())
