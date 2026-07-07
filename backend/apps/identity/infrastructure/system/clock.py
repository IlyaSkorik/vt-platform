"""System clock — the concrete :class:`Clock` adapter.

Implements the application's :class:`~apps.identity.application.interfaces.Clock`
port over the real wall clock, so use cases obtain the current instant through an
injected seam (deterministic and swappable under test) instead of calling
:func:`datetime.now` directly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from django.utils import timezone

__all__ = ["SystemClock"]


class SystemClock:
    """The current instant from the real clock, always timezone-aware."""

    def now(self) -> datetime:
        """The current instant in the platform's configured display timezone."""
        return timezone.localtime()

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware UTC datetime (API-000 §22)."""
        return datetime.now(UTC)
