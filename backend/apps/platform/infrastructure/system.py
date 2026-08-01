"""System adapters (clock, identifiers) for the Platform bounded context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.platform.infrastructure.models import uuid7

__all__ = ["SystemClock", "Uuid7Generator"]


class SystemClock:
    """Wall-clock adapter implementing the ``Clock`` port (always UTC)."""

    def utcnow(self) -> datetime:
        return datetime.now(UTC)


class Uuid7Generator:
    """Identifier adapter implementing the ``UuidGenerator`` port."""

    def new(self) -> uuid.UUID:
        return uuid7()
