"""``EventDispatcher`` — a synchronous, in-process ``EventPublisher`` adapter.

Concrete implementation of the
:class:`~apps.identity.application.interfaces.EventPublisher` port (ARCH-001 §4.8,
§7.3). Command handlers only *return* the events the domain produced; this adapter
is the seam that carries them to their consumers. It dispatches **synchronously,
in-process**, routing each event to the side-effect handlers registered for its
concrete type.

This is deliberately the simplest transport that closes the loop: registration
sends its verification email within the request. The port is unchanged, so a later
swap to a transactional outbox / Celery bus (for at-least-once, out-of-band
delivery) replaces only this adapter at the composition root — no handler,
use case, or domain code changes.

Failure policy: a subscriber's exception propagates. For the verification-email
flow that is intentional — if the email cannot be dispatched, the caller must not
report success as though it had been.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from apps.identity.domain.events import DomainEvent

__all__ = ["EventDispatcher"]

_E = TypeVar("_E", bound=DomainEvent)

#: A subscriber is any callable taking a single event and returning nothing.
_Subscriber = Callable[[DomainEvent], None]


class EventDispatcher:
    """Route domain events to synchronously-invoked, in-process subscribers.

    Subscribers are keyed by concrete event **type** and invoked in registration
    order for each matching event. Structurally satisfies the
    :class:`~apps.identity.application.interfaces.EventPublisher` port (it does not
    inherit the ``Protocol`` — the seam is structural by design).
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[_Subscriber]] = {}

    def subscribe(self, event_type: type[_E], handler: Callable[[_E], None]) -> None:
        """Register ``handler`` to be invoked for every event of ``event_type``."""
        # The public API is type-safe per (event_type, handler); internally we store
        # under the invariant base type, which is sound because dispatch only ever
        # calls a handler with an instance of the exact type it was registered for.
        subscriber: _Subscriber = handler  # type: ignore[assignment]
        self._subscribers.setdefault(event_type, []).append(subscriber)

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Dispatch ``events`` in order to every subscriber of each event's type."""
        for event in events:
            for handler in self._subscribers.get(type(event), ()):
                handler(event)
