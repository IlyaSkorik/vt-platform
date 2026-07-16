"""Ambient-dependency adapters (clock, uuid) for the Teacher Directory context."""

from __future__ import annotations

from apps.teachers.infrastructure.system.clock import SystemClock
from apps.teachers.infrastructure.system.uuids import Uuid7Generator

__all__ = ["SystemClock", "Uuid7Generator"]
