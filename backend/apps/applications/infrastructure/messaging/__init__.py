"""Messaging adapters for the Applications bounded context."""

from __future__ import annotations

from .event_dispatcher import NullEventPublisher

__all__ = ["NullEventPublisher"]
