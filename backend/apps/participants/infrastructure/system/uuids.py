"""UUID v7 generator — the concrete :class:`UuidGenerator` adapter.

Implements the application's
:class:`~apps.participants.application.interfaces.UuidGenerator` port, producing
time-ordered UUID version 7 identifiers (API-000 §23). It reuses the domain's own
UUID-v7 generation (via :meth:`ParticipantId.generate`) so a single, audited
implementation backs every identifier the context mints.
"""

from __future__ import annotations

import uuid

from apps.participants.domain.value_objects import ParticipantId

__all__ = ["Uuid7Generator"]


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        return ParticipantId.generate().value
