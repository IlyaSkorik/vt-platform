"""Composition root for the Competitions bounded context.

The one place framework-free use cases are wired to their concrete infrastructure
adapters (ARCH-001 §7.3, Dependency Inversion). The presentation edge asks this
module for a fully-assembled handler and stays ignorant of *which* repository,
clock, uuid source, or event transport sits behind each port. Swapping an adapter
(or a fake, in tests) changes only here.

Every command handler shares one constructor (``repository``, ``clock``,
``publisher``, ``uuids``), so a single generic builder assembles any of them;
query handlers take only the repository. All adapters are stateless and cheap, so
handlers are assembled per call — there is no shared mutable state.
"""

from __future__ import annotations

from apps.competitions.application.handlers import (
    GetCompetitionHandler,
    ListCompetitionsHandler,
)
from apps.competitions.application.handlers._support import CompetitionCommandHandler
from apps.competitions.infrastructure.messaging import EventDispatcher
from apps.competitions.infrastructure.read_models import DjangoPublicCatalogReader
from apps.competitions.infrastructure.repositories import DjangoCompetitionRepository
from apps.competitions.infrastructure.system import SystemClock, Uuid7Generator
from apps.organization.composition import build_organization_directory

__all__ = [
    "build_command_handler",
    "build_get_competition_handler",
    "build_list_competitions_handler",
    "build_public_catalog_read_service",
]


def build_command_handler[CommandHandlerT: CompetitionCommandHandler](handler_cls: type[CommandHandlerT]) -> CommandHandlerT:
    """Assemble any Competition command handler with its concrete adapters."""
    return handler_cls(
        repository=DjangoCompetitionRepository(),
        clock=SystemClock(),
        publisher=EventDispatcher(),
        uuids=Uuid7Generator(),
    )


def build_get_competition_handler() -> GetCompetitionHandler:
    """Assemble the single-competition read use case."""
    return GetCompetitionHandler(DjangoCompetitionRepository())


def build_list_competitions_handler() -> ListCompetitionsHandler:
    """Assemble the competition-listing read use case."""
    return ListCompetitionsHandler(DjangoCompetitionRepository())


def build_public_catalog_read_service() -> DjangoPublicCatalogReader:
    """Assemble the public festival catalog read model (participant-facing).

    A read-side projection, wired to the Organization directory read-port so it
    can render organizer identities without importing that context's aggregate.
    """
    return DjangoPublicCatalogReader(directory=build_organization_directory())
