"""ORM models (adapters) for the Identity & Access bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and
carry NO business logic. A package (not a single module) so models are split per
aggregate/entity. Each context maps to its own PostgreSQL schema (ARCH-001 §9.2);
tables are named with the ``identity_`` context prefix.

The domain layer remains the source of truth — these classes are only a database
representation the mapper/repository reads from and writes to.
"""

from __future__ import annotations

from .base import BasePersistenceModel, uuid7
from .consent import UserConsentModel
from .email_verification import UserEmailVerificationModel
from .phone_verification import UserPhoneVerificationModel
from .session import UserSessionModel
from .user import UserModel

__all__ = [
    "BasePersistenceModel",
    "UserConsentModel",
    "UserEmailVerificationModel",
    "UserModel",
    "UserPhoneVerificationModel",
    "UserSessionModel",
    "uuid7",
]
