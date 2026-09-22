"""ORM models (adapters) for the Finance bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and carry
NO business logic. Tables are named with the ``finance_`` context prefix. The
domain layer remains the source of truth — these classes are only a database
representation the mapper/repository reads from and writes to.
"""

from __future__ import annotations

from .base import BasePersistenceModel, uuid7
from .expense import PlatformExpenseModel

__all__ = [
    "BasePersistenceModel",
    "PlatformExpenseModel",
    "uuid7",
]
