"""Django ORM repository adapters for the Competitions bounded context.

The concrete implementations of the application repository ports (ARCH-001 §7.2,
§7.3): the only components permitted to touch the Django ORM on behalf of a
Competition aggregate. Use cases speak only aggregates and value objects; these
adapters turn those into model queries and back via the mappers, and translate
every Django exception into a :mod:`.exceptions` type so no framework error leaks.
"""

from __future__ import annotations

from .django_competition_repository import DjangoCompetitionRepository
from .exceptions import (
    ConcurrencyConflictError,
    IntegrityViolationError,
    PersistenceError,
    RepositoryError,
)

__all__ = [
    "ConcurrencyConflictError",
    "DjangoCompetitionRepository",
    "IntegrityViolationError",
    "PersistenceError",
    "RepositoryError",
]
