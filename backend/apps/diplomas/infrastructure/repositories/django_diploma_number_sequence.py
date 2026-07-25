"""Django adapter implementing the ``DiplomaNumberSequence`` port.

Reserving a value is one transaction: the scope's counter row is locked with
``SELECT … FOR UPDATE``, incremented, and written. Any concurrent worker blocks on
the lock until the first has committed, so two workers can never read the same
``current_number`` — the old ``max(number) + 1`` scan had exactly that race and is
gone.

The row for a scope is created on first use. ``get_or_create`` wraps its INSERT in
a savepoint and re-reads on conflict, so two workers racing the very first number
of a year both end up on the same row; the unique constraint on ``scope``
guarantees there is only ever one.

On SQLite (the test database) ``FOR UPDATE`` is not emitted — Django drops it for
backends without support — which is harmless: SQLite serializes writers anyway.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.diplomas.infrastructure.models import DiplomaNumberSequenceModel

__all__ = ["DjangoDiplomaNumberSequence"]


class DjangoDiplomaNumberSequence:
    """Concrete ``DiplomaNumberSequence`` over a locked counter row."""

    def next_value(self, *, scope: str) -> int:
        with transaction.atomic():
            DiplomaNumberSequenceModel.objects.get_or_create(
                scope=scope, defaults={"current_number": 0}
            )
            row = DiplomaNumberSequenceModel.objects.select_for_update().get(scope=scope)
            row.current_number += 1
            row.updated_at = timezone.now()
            row.version += 1
            row.save(update_fields=["current_number", "updated_at", "version"])
            return int(row.current_number)
