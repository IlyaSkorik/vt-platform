"""System adapters for the Competitions bounded context.

Concrete implementations of the ambient-dependency ports: the wall clock and the
UUID v7 generator, injected into use cases at the composition root.
"""

from __future__ import annotations

from .clock import SystemClock
from .uuids import Uuid7Generator

__all__ = ["SystemClock", "Uuid7Generator"]
