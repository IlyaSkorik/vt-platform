"""Domain <-> persistence mappers for the Identity & Access bounded context.

Translate between framework-free domain objects and Django ORM models, keeping
the domain ignorant of persistence (ARCH-001 §4.1, §7.2). The mapper is the sole
Anti-Corruption Layer allowed to know both the domain aggregates and the ORM
models; nothing else crosses that boundary.
"""

from __future__ import annotations

from .user_mapper import UserMapper

__all__ = ["UserMapper"]
