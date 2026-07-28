"""Small infrastructure adapters: the clock and the public-slug factory.

Both are ports the domain and use cases deliberately do not implement themselves -
time and randomness are effects, and injecting them is what makes a schedule test
deterministic and a slug collision testable.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.programs.domain.value_objects import PublicSlug

__all__ = ["RandomSlugFactory", "SystemClock"]


class SystemClock:
    """The real clock."""

    def utcnow(self) -> datetime:
        """The current UTC instant."""
        return datetime.now(UTC)


class RandomSlugFactory:
    """Mints public slugs from the domain's confusable-free alphabet."""

    def new_slug(self) -> str:
        """A fresh candidate slug (the caller checks it is free)."""
        return PublicSlug.generate().value
