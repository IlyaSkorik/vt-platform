"""UUID v7 generator — the concrete :class:`UuidGenerator` adapter.

Implements the application's
:class:`~apps.identity.application.interfaces.UuidGenerator` port, producing
time-ordered UUID version 7 identifiers (API-000 §23). It reuses the domain's own
UUID-v7 generation (via :meth:`UserId.generate`) so a single, audited
implementation backs every identifier the platform mints, rather than duplicating
the RFC 9562 bit-layout here.
"""

from __future__ import annotations

import uuid

from apps.identity.domain.value_objects import UserId

__all__ = ["Uuid7Generator"]


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        return UserId.generate().value
