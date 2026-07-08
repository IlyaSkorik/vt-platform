"""Ambient-dependency adapters for the Participants bounded context.

Concrete implementations of the time and identity ports declared in
:mod:`apps.participants.application.interfaces`, so use cases obtain "now" and fresh
identifiers through an injected seam rather than reading global state:

* :class:`SystemClock`    — the ``Clock`` port over the real wall clock.
* :class:`Uuid7Generator` — the ``UuidGenerator`` port producing UUID v7 values.
"""

from __future__ import annotations

from apps.participants.infrastructure.system.clock import SystemClock
from apps.participants.infrastructure.system.uuids import Uuid7Generator

__all__ = ["SystemClock", "Uuid7Generator"]
