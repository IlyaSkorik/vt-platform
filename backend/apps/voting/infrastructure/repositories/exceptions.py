"""Infrastructure-level persistence errors for the Voting bounded context.

Repositories translate every Django exception into one of these, so no framework
error leaks past the boundary (ARCH-001 §7.2).
"""

from __future__ import annotations

__all__ = ["ConcurrencyConflictError", "IntegrityViolationError", "PersistenceError"]


class PersistenceError(Exception):
    """A database operation failed for a reason the caller cannot act on."""


class ConcurrencyConflictError(PersistenceError):
    """The row moved under us: someone else saved this aggregate first."""


class IntegrityViolationError(PersistenceError):
    """The write violated a database constraint."""
