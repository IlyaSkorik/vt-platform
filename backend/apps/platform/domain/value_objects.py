"""Value objects for the Platform bounded context.

Immutable, identity-less concepts of the platform operator's own domain. Frozen,
slotted dataclasses that validate on construction and compare by value. **Pure
domain code** (ARCH-001 §4.1, §7.2): standard library only.

* :class:`PlatformAdministratorId` — UUID v7 identity of an administrator grant.
* :class:`PlatformUserId`          — UUID v7 reference to an Identity user (opaque here).

The id logic is deliberately duplicated from the neighbouring contexts rather
than shared: the contexts stay independent, with no import edge (ARCH-001 §14).
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Final

from .exceptions import InvalidPlatformAdministratorIdError, InvalidPlatformUserIdError

__all__ = ["PlatformAdministratorId", "PlatformUserId"]

_UUID_V7_VERSION: Final = 7


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7."""
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


@dataclass(frozen=True, slots=True, repr=False)
class PlatformAdministratorId:
    """The identity of one administrator grant (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidPlatformAdministratorIdError(f"PlatformAdministratorId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidPlatformAdministratorIdError(f"PlatformAdministratorId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> PlatformAdministratorId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> PlatformAdministratorId:
        return cls(value)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"PlatformAdministratorId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class PlatformUserId:
    """A reference to the Identity account holding the grant, held as an opaque UUID."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidPlatformUserIdError(f"PlatformUserId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidPlatformUserIdError(f"PlatformUserId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> PlatformUserId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> PlatformUserId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidPlatformUserIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"PlatformUserId({str(self.value)!r})"
