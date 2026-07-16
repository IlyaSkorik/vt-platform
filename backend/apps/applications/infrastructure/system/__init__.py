"""Ambient-dependency adapters (clock, uuid) for the Applications context."""

from __future__ import annotations

from apps.applications.infrastructure.system.clock import SystemClock
from apps.applications.infrastructure.system.uuids import Uuid7Generator

__all__ = ["SystemClock", "Uuid7Generator"]
