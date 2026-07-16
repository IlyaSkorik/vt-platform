"""Event-publishing adapter for the Applications bounded context.

The application layer only *collects* domain events; publishing them onto a real
transport (a transactional outbox / bus) is a future concern (ARCH-001 §4.8). Until
that transport exists, this no-op adapter satisfies the ``EventPublisher`` port so
handlers can be composed and run end to end without a message bus. Swapping in a
real outbox later changes only this module and the composition root.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.applications.domain.events import DomainEvent

__all__ = ["NullEventPublisher"]


class NullEventPublisher:
    """An ``EventPublisher`` that accepts and discards events (no transport yet)."""

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Accept ``events`` and drop them; a future outbox will forward them."""
        return None
