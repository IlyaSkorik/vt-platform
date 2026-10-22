"""ACL adapters over sibling bounded contexts for the Judging application.

Four windows, and the direction each one points matters: the competition, performance
and account directories **read** (Competitions, Applications, Programs, Identity), the
protocol writer **writes** (Results). Nothing outward of this package knows any of those
contexts exist.
"""

from __future__ import annotations

from .account_directory import DjangoAccountDirectory
from .competition_directory import DjangoCompetitionDirectory
from .performance_directory import COMPETING_SUBMISSION_STATUSES, DjangoPerformanceDirectory
from .protocol_writer import ResultsProtocolWriter

__all__ = [
    "COMPETING_SUBMISSION_STATUSES",
    "DjangoAccountDirectory",
    "DjangoCompetitionDirectory",
    "DjangoPerformanceDirectory",
    "ResultsProtocolWriter",
]
