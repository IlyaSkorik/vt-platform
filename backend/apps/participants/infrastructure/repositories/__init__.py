"""Repository implementations for the Participants bounded context.

ORM-backed adapters implementing the ports in application/interfaces.py
(ARCH-001 §7.2) — the only gateway between aggregates and persistence. A package so
repositories can be split per aggregate.
"""

from __future__ import annotations

from .django_participant_repository import DjangoParticipantRepository
from .exceptions import (
    ConcurrencyConflictError,
    IntegrityViolationError,
    PersistenceError,
    RepositoryError,
)

__all__ = [
    "ConcurrencyConflictError",
    "DjangoParticipantRepository",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]
