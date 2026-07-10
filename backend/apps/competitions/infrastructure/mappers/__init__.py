"""Domain <-> persistence mappers for the Competitions bounded context.

Translate between framework-free domain objects and Django ORM models, keeping the
domain ignorant of persistence (ARCH-001 §4.1, §7.2). The mapper is the single
component that knows both sides; the repository drives it and owns persistence
timing and child-row synchronization.
"""

from __future__ import annotations

from .competition_mapper import CompetitionChildRows, CompetitionMapper

__all__ = ["CompetitionChildRows", "CompetitionMapper"]
