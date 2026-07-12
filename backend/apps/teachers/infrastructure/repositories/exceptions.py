"""Repository-layer exceptions for the Teacher Directory bounded context.

Persistence adapters must never let a **framework** exception escape into the
application layer (ARCH-001 §7.2, §7.6). This module is the infrastructure's own
error vocabulary; every Django/ORM failure is translated into one of these types
before it crosses the boundary.

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
    """Base class for every failure raised by a Teachers persistence adapter."""


class ConcurrencyConflictError(RepositoryError):
    """A write lost an optimistic-concurrency race (stale ``version``)."""


class IntegrityViolationError(RepositoryError):
    """A database integrity constraint rejected the write."""


class PersistenceError(RepositoryError):
    """A database or driver error that is not a constraint or concurrency clash."""
