"""UUID v7 generator — the concrete :class:`UuidGenerator` adapter.

Produces time-ordered UUID version 7 identifiers (API-000 §23) via the domain's
own generation helper, so a single implementation backs every id this context
mints.
"""

from __future__ import annotations

import uuid

from apps.organization.domain.value_objects import _generate_uuid7

__all__ = ["Uuid7Generator"]


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        return _generate_uuid7()
