"""Domain <-> persistence mappers for the Applications bounded context.

Translate between framework-free domain objects and Django ORM models, keeping the
domain ignorant of persistence (ARCH-001 §4.1, §7.2).
"""

from __future__ import annotations

from .application_mapper import ApplicationMapper
from .submission_mapper import SubmissionMapper

__all__ = ["ApplicationMapper", "SubmissionMapper"]
