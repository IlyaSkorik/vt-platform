"""Repository implementations for the Identity & Access bounded context.

ORM-backed adapters implementing the ports in application/interfaces.py and
domain/interfaces.py (ARCH-001 §7.2) — the only gateway between aggregates and
persistence. A package so repositories can be split per aggregate.
"""

from __future__ import annotations

from .django_consent_journal import DjangoConsentJournal
from .django_user_repository import DjangoUserRepository
from .exceptions import (
    ConcurrencyConflictError,
    IntegrityViolationError,
    PersistenceError,
    RepositoryError,
)

__all__ = [
    "ConcurrencyConflictError",
    "DjangoConsentJournal",
    "DjangoUserRepository",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]
