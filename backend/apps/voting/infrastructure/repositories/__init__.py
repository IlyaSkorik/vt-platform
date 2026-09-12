"""Django ORM repository adapters for the Voting bounded context.

The concrete implementations of the application repository ports (ARCH-001 §7.2,
§7.3): the only components permitted to touch the Django ORM on behalf of this
context. Use cases speak aggregates and value objects; these adapters turn those
into model queries and back via the mappers, and translate every Django exception
into a :mod:`.exceptions` type so no framework error leaks.
"""

from __future__ import annotations

from .django_ballot_repository import DjangoBallotRepository
from .django_vote_repository import DjangoVoteRepository
from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = [
    "ConcurrencyConflictError",
    "DjangoBallotRepository",
    "DjangoVoteRepository",
    "IntegrityViolationError",
    "PersistenceError",
]
