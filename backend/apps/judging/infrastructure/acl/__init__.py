"""ACL adapters over sibling bounded contexts for the Judging application.

Three windows, and the direction each one points matters: the competition and the
performance directories **read** (Competitions, Applications, Programs), the protocol
writer **writes** (Results). Nothing outward of this package knows any of those contexts
exist.
"""

from __future__ import annotations

from .competition_directory import DjangoCompetitionDirectory
from .performance_directory import COMPETING_SUBMISSION_STATUSES, DjangoPerformanceDirectory
from .protocol_writer import ResultsProtocolWriter

__all__ = [
    "COMPETING_SUBMISSION_STATUSES",
    "DjangoCompetitionDirectory",
    "DjangoPerformanceDirectory",
    "ResultsProtocolWriter",
]
