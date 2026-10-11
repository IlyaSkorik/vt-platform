"""Composition root for the Programs bounded context.

The one place a framework-free use case is wired to its concrete adapters
(ARCH-001 §7.3, Dependency Inversion): the presentation edge asks here for an
assembled service and stays ignorant of which repository, catalog or clock sits
behind each port. Adapters are stateless and cheap, so they are assembled per call.
"""

from __future__ import annotations

from apps.programs.application.services import ProgramService
from apps.programs.infrastructure.acl import DjangoPerformanceCatalog
from apps.programs.infrastructure.messaging import DjangoProgramNotifier
from apps.programs.infrastructure.pdf import ReportLabTableRenderer
from apps.programs.infrastructure.repositories import DjangoProgramRepository
from apps.programs.infrastructure.system import RandomSlugFactory, SystemClock

__all__ = ["build_program_service"]


def build_program_service() -> ProgramService:
    """Assemble the program use cases over PostgreSQL, the real clock and a PDF renderer."""
    return ProgramService(
        programs=DjangoProgramRepository(),
        catalog=DjangoPerformanceCatalog(),
        clock=SystemClock(),
        slugs=RandomSlugFactory(),
        tables=ReportLabTableRenderer(),
        notifier=DjangoProgramNotifier(),
    )
