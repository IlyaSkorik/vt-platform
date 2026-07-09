"""System adapters for the Organization bounded context (clock, UUID generation).

Concrete implementations of the ambient-dependency ports
(:class:`~apps.organization.application.interfaces.Clock`,
:class:`~apps.organization.application.interfaces.UuidGenerator`) so use cases
obtain time and identity through injected seams instead of reading globals.
"""

from __future__ import annotations

from .clock import SystemClock
from .uuids import Uuid7Generator

__all__ = ["SystemClock", "Uuid7Generator"]
