"""Domain <-> persistence mappers for the Participants bounded context.

Translate between framework-free domain objects and Django ORM models, keeping the
domain ignorant of persistence (ARCH-001 §4.1, §7.2). The mapper is the sole
Anti-Corruption Layer allowed to know both the domain aggregates and the ORM
models; nothing else crosses that boundary.
"""

from __future__ import annotations

from .participant_mapper import ParticipantMapper

__all__ = ["ParticipantMapper"]
