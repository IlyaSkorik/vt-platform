"""ACL adapters over sibling bounded contexts for the Results application.

Four windows onto other contexts, and the direction each one points matters: the catalog,
the running order and the award vocabulary **read** (Applications, Competitions, Programs,
Judging), the award register **writes** (Diplomas). Nothing outward of this package knows
any of those contexts exist.
"""

from __future__ import annotations

from .award_register import DiplomasAwardRegister
from .award_vocabulary import JudgingAwardVocabulary
from .performance_catalog import COMPETING_SUBMISSION_STATUSES, DjangoPerformanceCatalog
from .running_order import DjangoRunningOrderSource

__all__ = [
    "COMPETING_SUBMISSION_STATUSES",
    "DiplomasAwardRegister",
    "DjangoPerformanceCatalog",
    "DjangoRunningOrderSource",
    "JudgingAwardVocabulary",
]
