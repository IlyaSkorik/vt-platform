"""Repository implementations for the Applications bounded context.

ORM-backed adapters implementing the ports in ``application/interfaces.py``
(ARCH-001 §7.2) - the only gateway between aggregates and persistence.
"""

from __future__ import annotations

from .django_application_repository import DjangoApplicationRepository
from .django_submission_repository import DjangoSubmissionRepository
from .exceptions import (
    ConcurrencyConflictError,
    IntegrityViolationError,
    PersistenceError,
    RepositoryError,
)

__all__ = [
    "ConcurrencyConflictError",
    "DjangoApplicationRepository",
    "DjangoSubmissionRepository",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]
