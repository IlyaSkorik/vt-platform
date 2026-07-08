"""Repository-layer exceptions for the Participants bounded context.

Persistence adapters must never let a **framework** exception escape into the
application layer (ARCH-001 §7.2, §7.6): a use case depends on the
:class:`~apps.participants.application.interfaces.ParticipantRepository` *port*, not
on Django, so it may not be forced to ``except django.db.IntegrityError``. This
module is the infrastructure's own error vocabulary — every Django/ORM failure a
repository can hit is translated into one of these types before it crosses the
boundary.

The hierarchy is intentionally shallow:

    RepositoryError                 — base for every persistence-adapter failure
    ├── ConcurrencyConflictError    — optimistic-lock clash (stale ``version``)
    ├── IntegrityViolationError     — a database constraint rejected the write
    │                                 (translated from ``IntegrityError``)
    └── PersistenceError            — any other database/driver failure
                                      (translated from ``DatabaseError``)

These are **infrastructure** errors, not domain or application ones: they signal a
storage-level fault (a lost race, a violated constraint, an unreachable database),
never a business-rule violation.
"""

from __future__ import annotations

__all__ = [
    "ConcurrencyConflictError",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]


class RepositoryError(Exception):
    """Base class for every failure raised by a Participants persistence adapter."""


class ConcurrencyConflictError(RepositoryError):
    """A write lost an optimistic-concurrency race.

    Raised by :meth:`save` when the row's stored ``version`` no longer matches the
    version the in-memory aggregate was loaded at — another transaction mutated the
    same participant in between. The caller should reload the aggregate and retry.
    """


class IntegrityViolationError(RepositoryError):
    """A database integrity constraint rejected the write.

    The translation of :class:`django.db.IntegrityError` — most often the partial
    unique constraint on an active display alias
    (``participants_unique_active_display_alias``) or the per-participant guardian
    uniqueness, i.e. a clash that slipped past the application-level pre-check
    because a concurrent writer inserted the same value first.
    """


class PersistenceError(RepositoryError):
    """A database or driver error that is not a constraint or concurrency clash.

    The catch-all translation of :class:`django.db.DatabaseError` (connection loss,
    serialization failure, operational error). It exists so that *no* raw Django
    exception ever escapes the infrastructure layer.
    """
