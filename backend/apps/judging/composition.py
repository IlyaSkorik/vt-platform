"""Composition root for the Judging bounded context.

The one place a framework-free use case is wired to its concrete adapters (ARCH-001
§7.3, Dependency Inversion): the presentation edge asks here for an assembled service
and stays ignorant of which repository, clock, directory or mail gateway sits behind
each port. Adapters are stateless and cheap, so they are assembled per call.

Two services rather than one, because two different things happen here — see the module
docstring of :mod:`apps.judging.application.services`.
"""

from __future__ import annotations

from apps.judging.application.services import JudgingConfigurationService, ScoringService
from apps.judging.infrastructure.acl import (
    DjangoCompetitionDirectory,
    DjangoPerformanceDirectory,
    ResultsProtocolWriter,
)
from apps.judging.infrastructure.messaging import DjangoJuryNotifier
from apps.judging.infrastructure.repositories import (
    DjangoJudgingSetupRepository,
    DjangoJuryMemberRepository,
    DjangoPerformanceScoringRepository,
    DjangoScorecardRepository,
)
from apps.judging.infrastructure.system import (
    InviteTokenFactory,
    RandomSlugFactory,
    SystemClock,
    Uuid7Generator,
)

__all__ = ["build_judging_configuration_service", "build_scoring_service"]


def build_judging_configuration_service() -> JudgingConfigurationService:
    """Assemble the organizer's setup use cases over PostgreSQL and real mail."""
    return JudgingConfigurationService(
        setups=DjangoJudgingSetupRepository(),
        members=DjangoJuryMemberRepository(),
        competitions=DjangoCompetitionDirectory(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        slugs=RandomSlugFactory(),
        tokens=InviteTokenFactory(),
        notifier=DjangoJuryNotifier(),
    )


def build_scoring_service() -> ScoringService:
    """Assemble the festival-day use cases over PostgreSQL and the real clock."""
    return ScoringService(
        setups=DjangoJudgingSetupRepository(),
        members=DjangoJuryMemberRepository(),
        scorings=DjangoPerformanceScoringRepository(),
        scorecards=DjangoScorecardRepository(),
        competitions=DjangoCompetitionDirectory(),
        performances=DjangoPerformanceDirectory(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        protocols=ResultsProtocolWriter(),
    )
