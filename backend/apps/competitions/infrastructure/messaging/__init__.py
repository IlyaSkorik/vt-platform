"""Messaging adapters for the Competitions bounded context.

Concrete implementations of the outbound side-effect ports — currently the
in-process event dispatcher that carries recorded domain events to consumers.
"""

from __future__ import annotations

from .event_dispatcher import EventDispatcher

__all__ = ["EventDispatcher"]
