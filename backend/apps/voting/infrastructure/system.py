"""Small infrastructure adapters: the clock, ids and the public-slug factory.

Ports the domain and the use cases deliberately do not implement themselves —
time, randomness and identity are effects, and injecting them is what makes a
ballot's behaviour testable without waiting for midnight.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

from apps.voting.domain.value_objects import PublicSlug

__all__ = ["RandomSlugFactory", "SystemClock", "Uuid7Generator"]

_UUID_V7_VERSION = 7


class SystemClock:
    """The real clock."""

    def utcnow(self) -> datetime:
        """The current UTC instant."""
        return datetime.now(UTC)


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        unix_ms = time.time_ns() // 1_000_000
        rand = int.from_bytes(os.urandom(10), "big")
        rand_a = (rand >> 68) & 0x0FFF
        rand_b = rand & ((1 << 62) - 1)
        value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
        return uuid.UUID(int=value)


class RandomSlugFactory:
    """Mints public slugs from the domain's confusable-free alphabet."""

    def new_slug(self) -> str:
        """A fresh candidate slug (the caller checks it is free)."""
        return PublicSlug.generate().value
