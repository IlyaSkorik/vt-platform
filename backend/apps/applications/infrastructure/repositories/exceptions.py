"""Repository-layer exceptions for the Applications bounded context.

Persistence adapters translate every Django/ORM failure into one of these types
before it crosses into the application layer (ARCH-001 §7.2, §7.6).

    RepositoryError                 - base for every persistence-adapter failure
    ├── ConcurrencyConflictError    - optimistic-lock clash (stale ``version``)
    ├── IntegrityViolationError     - a database constraint rejected the write
    └── PersistenceError            - any other database/driver failure
"""

from __future__ import annotations

__all__ = [
    "ConcurrencyConflictError",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]


class RepositoryError(Exception):
    """Base class for every failure raised by an Applications persistence adapter."""


class ConcurrencyConflictError(RepositoryError):
    """A write lost an optimistic-concurrency race (stale ``version``)."""


class IntegrityViolationError(RepositoryError):
    """A database integrity constraint rejected the write."""


class PersistenceError(RepositoryError):
    """A database or driver error that is not a constraint or concurrency clash."""
