"""``EventDispatcher`` — a synchronous, in-process ``EventPublisher`` adapter.

Concrete implementation of the
:class:`~apps.organization.application.interfaces.EventPublisher` port. Command
handlers only *return* the events the domain produced; this adapter carries them
to consumers, dispatching **synchronously, in-process**, routing each event to
the side-effect handlers registered for its concrete type. A later swap to a
transactional outbox / Celery bus replaces only this adapter at the composition
root — no handler, use case, or domain code changes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from apps.organization.domain.events import DomainEvent

__all__ = ["EventDispatcher"]

_E = TypeVar("_E", bound=DomainEvent)

_Subscriber = Callable[[DomainEvent], None]


class EventDispatcher:
    """Route domain events to synchronously-invoked, in-process subscribers.

    Subscribers are keyed by concrete event **type** and invoked in registration
    order. Structurally satisfies the ``EventPublisher`` port (no ``Protocol``
    inheritance — the seam is structural by design).
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[_Subscriber]] = {}

    def subscribe(self, event_type: type[_E], handler: Callable[[_E], None]) -> None:
        """Register ``handler`` to be invoked for every event of ``event_type``."""
        subscriber: _Subscriber = handler  # type: ignore[assignment]
        self._subscribers.setdefault(event_type, []).append(subscriber)

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Dispatch ``events`` in order to every subscriber of each event's type."""
        for event in events:
            for handler in self._subscribers.get(type(event), ()):
                handler(event)
