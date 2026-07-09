"""Shared optimistic-concurrency upsert for Organization repositories.

Every Organization aggregate owns a ``version`` bumped once per mutation. This
helper implements the "one business operation per save" write shared by all three
repositories: an ``UPDATE … WHERE id = ? AND version = current - 1`` maps a stale
read to zero rows (→ :class:`ConcurrencyConflictError` if the row still exists),
while a freshly created aggregate falls through to an ``INSERT``. The whole
classify-then-write runs in one transaction.
"""

from __future__ import annotations

import uuid

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Model

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["optimistic_upsert"]


def optimistic_upsert(
    *,
    model_cls: type[Model],
    pk: uuid.UUID,
    version: int,
    columns: dict[str, object],
) -> None:
    """Insert or version-checked update the row for ``pk`` from ``columns``.

    ``version`` is the aggregate's *current* version (already advanced for this
    mutation); the update is conditional on the previous one. Translates every
    Django exception into an infrastructure error so none escapes the boundary.
    """
    update_values = {name: value for name, value in columns.items() if name != "id"}
    previous_version = version - 1
    manager = model_cls._default_manager
    try:
        with transaction.atomic():
            updated = manager.filter(pk=pk, version=previous_version).update(**update_values)
            if updated:
                return
            if manager.filter(pk=pk).exists():
                raise ConcurrencyConflictError(f"{model_cls.__name__} {pk} was modified concurrently; expected version {previous_version}.")
            manager.create(**columns)
    except IntegrityError as exc:
        raise IntegrityViolationError(f"Failed to persist {model_cls.__name__} {pk}.") from exc
    except DatabaseError as exc:  # pragma: no cover - defensive
        raise PersistenceError(f"Failed to persist {model_cls.__name__} {pk}.") from exc
