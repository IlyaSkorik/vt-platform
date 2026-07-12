"""UUID v7 generator - the concrete :class:`UuidGenerator` adapter (API-000 §23)."""

from __future__ import annotations

import uuid

from apps.applications.domain.value_objects import SubmissionId

__all__ = ["Uuid7Generator"]


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        return SubmissionId.generate().value
