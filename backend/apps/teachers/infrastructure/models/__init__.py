"""ORM models (adapters) for the Teacher Directory bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and carry
NO business logic. Tables are named with the ``teachers_`` context prefix.
"""

from __future__ import annotations

from .base import BasePersistenceModel, uuid7
from .teacher import TeacherModel

__all__ = ["BasePersistenceModel", "TeacherModel", "uuid7"]
