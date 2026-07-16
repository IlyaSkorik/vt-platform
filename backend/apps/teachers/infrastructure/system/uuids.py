"""UUID v7 generator - the concrete :class:`UuidGenerator` adapter (API-000 §23).

Reuses the domain's own UUID-v7 generation (via :meth:`TeacherId.generate`) so a
single implementation backs every identifier the context mints.
"""

from __future__ import annotations

import uuid

from apps.teachers.domain.value_objects import TeacherId

__all__ = ["Uuid7Generator"]


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        return TeacherId.generate().value
