"""Value objects for the Teacher Directory bounded context.

Immutable, identity-less concepts of the Teacher domain. Each is a frozen, slotted
dataclass that validates on construction, compares by value, and can never be
mutated. **Pure domain code** (ARCH-001 §4.1, §7.2): standard library only - no
Django, no ORM, no third-party validators.

The id value objects intentionally duplicate the UUID-v7 logic that also exists in
the sibling contexts: the bounded contexts stay independent (no shared import
edge), so a little duplication is preferred over a cross-context dependency
(ARCH-001 §14).
"""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .exceptions import (
    InvalidEmailAddressError,
    InvalidOwnerIdError,
    InvalidPersonNameError,
    InvalidPhoneNumberError,
    InvalidTeacherIdError,
    InvalidTeacherRoleError,
)

__all__ = [
    "ConsentReference",
    "EmailAddress",
    "OwnerId",
    "PersonName",
    "PhoneNumber",
    "TeacherId",
    "TeacherRole",
    "TeacherStatus",
]

_UUID_V7_VERSION: Final = 7

_FIRST_NAME_MAX: Final = 120
_LAST_NAME_MAX: Final = 120
_MIDDLE_NAME_MAX: Final = 120
_TEACHER_ROLE_MAX: Final = 120
_EMAIL_MAX: Final = 320
_PHONE_MAX: Final = 32
_EMAIL_RE: Final = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE: Final = re.compile(r"^\+?[0-9][0-9\s\-()]{4,}$")


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7.

    Implemented directly rather than via ``uuid.uuid7`` (added only in Python 3.14)
    so the domain works on any supported interpreter.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = rand >> 68 & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class TeacherId:
    """The globally unique identity of a :class:`~apps.teachers.domain.entities.Teacher` (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidTeacherIdError(f"TeacherId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidTeacherIdError(f"TeacherId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> TeacherId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> TeacherId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> TeacherId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidTeacherIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TeacherId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class OwnerId:
    """A reference to the authenticated user who owns the directory entry (opaque UUID v7).

    A separate type from the Identity context's own user id so the two contexts
    share no import edge (ARCH-001 §14). Teachers belong to a user - never to a
    competition or a participant.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidOwnerIdError(f"OwnerId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidOwnerIdError(f"OwnerId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> OwnerId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> OwnerId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidOwnerIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OwnerId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# Content value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersonName:
    """A teacher's name - last and first required, middle (patronymic) optional."""

    first_name: str
    last_name: str
    middle_name: str | None = None

    def __post_init__(self) -> None:
        first = self.first_name.strip()
        last = self.last_name.strip()
        if not first:
            raise InvalidPersonNameError("First name must not be empty.")
        if not last:
            raise InvalidPersonNameError("Last name must not be empty.")
        if len(first) > _FIRST_NAME_MAX:
            raise InvalidPersonNameError(f"First name must be at most {_FIRST_NAME_MAX} characters.")
        if len(last) > _LAST_NAME_MAX:
            raise InvalidPersonNameError(f"Last name must be at most {_LAST_NAME_MAX} characters.")
        object.__setattr__(self, "first_name", first)
        object.__setattr__(self, "last_name", last)
        if self.middle_name is not None:
            middle = self.middle_name.strip()
            if not middle:
                object.__setattr__(self, "middle_name", None)
            elif len(middle) > _MIDDLE_NAME_MAX:
                raise InvalidPersonNameError(f"Middle name must be at most {_MIDDLE_NAME_MAX} characters.")
            else:
                object.__setattr__(self, "middle_name", middle)

    @property
    def full_name(self) -> str:
        """The name rendered ``Last First [Middle]``."""
        parts = [self.last_name, self.first_name]
        if self.middle_name is not None:
            parts.append(self.middle_name)
        return " ".join(parts)

    def __str__(self) -> str:
        return self.full_name


@dataclass(frozen=True, slots=True)
class TeacherRole:
    """A configurable teacher role label (e.g. Teacher, Concertmaster, Choreographer)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidTeacherRoleError("Teacher role must not be empty.")
        if len(stripped) > _TEACHER_ROLE_MAX:
            raise InvalidTeacherRoleError(f"Teacher role must be at most {_TEACHER_ROLE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """A syntactically valid, length-bounded email address (optional contact)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidEmailAddressError("Email must not be empty.")
        if len(stripped) > _EMAIL_MAX:
            raise InvalidEmailAddressError(f"Email must be at most {_EMAIL_MAX} characters.")
        if not _EMAIL_RE.match(stripped):
            raise InvalidEmailAddressError(f"{stripped!r} is not a valid email address.")
        object.__setattr__(self, "value", stripped.lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    """A loosely-validated, length-bounded phone number (optional contact)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidPhoneNumberError("Phone number must not be empty.")
        if len(stripped) > _PHONE_MAX:
            raise InvalidPhoneNumberError(f"Phone number must be at most {_PHONE_MAX} characters.")
        if not _PHONE_RE.match(stripped):
            raise InvalidPhoneNumberError(f"{stripped!r} is not a valid phone number.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TeacherStatus(StrEnum):
    """A directory entry's lifecycle state.

    ``ACTIVE``   - shown in the directory and selectable when building an application.
    ``ARCHIVED`` - hidden from the directory but preserved (past applications that
                   snapshotted this teacher keep their own copy); can be reactivated.
    """

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class ConsentReference:
    """A by-identity reference to the Identity consent that authorizes this entry.

    A teacher in somebody's directory is an adult whose details were entered by
    somebody else, so the basis for holding them is that adult's own consent, obtained
    by whoever entered them (LEGAL-001 §5.4). This context records only the reference —
    the consent's UUID and the exact version of the text accepted — never the text
    itself, which belongs to Identity. Compared by value.
    """

    consent_id: uuid.UUID
    consent_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.consent_id, uuid.UUID):  # defensive: wrong type
            raise ValueError("ConsentReference.consent_id must be a uuid.UUID.")
        version = self.consent_version.strip()
        if not version or len(version) > 40:
            raise ValueError("ConsentReference.consent_version must be non-empty and at most 40 characters.")
        object.__setattr__(self, "consent_version", version)

    @classmethod
    def of(cls, consent_id: str | uuid.UUID, consent_version: str) -> ConsentReference:
        """Build from a raw id, parsing it at the boundary."""
        parsed = consent_id if isinstance(consent_id, uuid.UUID) else uuid.UUID(str(consent_id))
        return cls(consent_id=parsed, consent_version=consent_version)
