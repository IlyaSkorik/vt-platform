"""Composition root for the Results bounded context.

The one place a framework-free use case is wired to its concrete adapters (ARCH-001 §7.3,
Dependency Inversion): the presentation edge asks here for an assembled service and stays
ignorant of which repository, catalog, diploma register or mail gateway sits behind each
port. Adapters are stateless and cheap, so they are assembled per call.
"""

from __future__ import annotations

from apps.results.application.services import ProtocolService
from apps.results.infrastructure.acl import (
    DiplomasAwardRegister,
    DjangoPerformanceCatalog,
    DjangoRunningOrderSource,
    JudgingAwardVocabulary,
)
from apps.results.infrastructure.messaging import DjangoResultsNotifier
from apps.results.infrastructure.repositories import DjangoProtocolRepository
from apps.results.infrastructure.system import RandomSlugFactory, SystemClock

__all__ = ["build_protocol_service"]


def build_protocol_service() -> ProtocolService:
    """Assemble the protocol use cases over PostgreSQL, the real clock and real mail."""
    return ProtocolService(
        protocols=DjangoProtocolRepository(),
        catalog=DjangoPerformanceCatalog(),
        running_order=DjangoRunningOrderSource(),
        clock=SystemClock(),
        slugs=RandomSlugFactory(),
        vocabulary=JudgingAwardVocabulary(),
        awards=DiplomasAwardRegister(),
        notifier=DjangoResultsNotifier(),
    )
