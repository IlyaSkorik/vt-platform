"""Value objects for the Participants bounded context.

Immutable, identity-less concepts of the Participants domain (DATA-001 §8, §4.2).
Every value object here is a frozen, slotted dataclass: it validates its input on
construction, is compared by value, and can never be mutated afterwards.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no Pydantic. Persistence and transport live in outer
layers and depend on these types — never the other way around. Keeping these
invariants in the domain means an invalid ``DateOfBirth`` or ``DisplayAlias``
simply cannot exist at runtime, so no outer layer has to re-check them.

Value objects implemented here:

* :class:`ParticipantId`  — UUID v7 identity of a participant (non-enumerable; DIA-001 §4.2).
* :class:`GuardianId`     — UUID v7 reference to a guardian.
* :class:`TeacherId`      — UUID v7 reference to a teacher.
* :class:`InstitutionId`  — UUID v7 cross-context reference to an institution.
* :class:`PersonName`     — given / family / optional middle (patronymic) name (DATA-001 §8).
* :class:`DateOfBirth`    — a validated birth date, source of the derived age group (PRT-002).
* :class:`AgeGroup`       — a derived, tamper-resistant age band (PRT-002).
* :class:`DisplayAlias`   — the pseudonym shown to judging (JDG-006, DATA-001 §4.2).
* :class:`ConsentReference` — a by-id reference to the Identity consent that authorizes a minor.
* :class:`ActorReference` — the adult (guardian/teacher) acting for the participant.
* :class:`GuardianLink`   — a guardian↔participant relationship inside the aggregate (DIA-001 §4.2).
* :class:`InstitutionAuthority` — an authorizing institution (+ optional teacher) link (PRT-001).

Enumerations (self-documenting classifiers used across the domain):

* :class:`ParticipantStatus`       — the aggregate's lifecycle state (DATA-004 §4.3).
* :class:`RelationshipStatus`      — a guardian link's lifecycle state (DATA-001 §4.2).
* :class:`GuardianRelationshipType`— the kind of guardian relationship.
* :class:`ActorType`               — whether an actor is a guardian or a teacher.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum
from typing import Final

from .exceptions import (
    InvalidConsentReferenceError,
    InvalidDateOfBirthError,
    InvalidDisplayAliasError,
    InvalidGuardianIdError,
    InvalidInstitutionIdError,
    InvalidParticipantIdError,
    InvalidPersonNameError,
    InvalidTeacherIdError,
    ValueObjectValidationError,
)

__all__ = [
    "ActorReference",
    "ActorType",
    "AgeGroup",
    "ConsentReference",
    "DateOfBirth",
    "DisplayAlias",
    "GuardianId",
    "GuardianLink",
    "GuardianRelationshipType",
    "InstitutionAuthority",
    "InstitutionId",
    "ParticipantId",
    "ParticipantStatus",
    "PersonName",
    "RelationshipStatus",
    "TeacherId",
]

_UUID_V7_VERSION: Final = 7


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7.

    Implemented directly rather than via ``uuid.uuid7`` (added only in Python
    3.14) so the domain works on any supported interpreter. The time-ordered
    layout keeps primary keys roughly monotonic, avoiding the index fragmentation
    random UUID v4 keys cause at database scale.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (
        (unix_ms & ((1 << 48) - 1)) << 80
        | _UUID_V7_VERSION << 76
        | rand_a << 64
        | 0b10 << 62
        | rand_b
    )
    return uuid.UUID(int=value)


def _parse_uuid(value: str, *, error: type[ValueObjectValidationError], label: str) -> uuid.UUID:
    """Parse a canonical UUID string, raising ``error`` on any failure."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise error(f"{value!r} is not a valid UUID string for {label}.") from exc


def _ensure_uuid7(value: uuid.UUID, *, error: type[ValueObjectValidationError], label: str) -> None:
    """Guard that ``value`` is a :class:`uuid.UUID` of version 7."""
    if not isinstance(value, uuid.UUID):  # defensive: wrong type
        raise error(f"{label} must wrap a uuid.UUID, got {type(value)!r}.")
    if value.version != _UUID_V7_VERSION:
        raise error(f"{label} must be a UUID v7, got version {value.version}.")


# ---------------------------------------------------------------------------
# Identifiers (aggregate identity + cross-context references)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class ParticipantId:
    """The globally unique identity of a participant (DIA-001 §4.2).

    Wraps a time-ordered **UUID v7** (API-000 §23) so identifiers are globally
    unique, non-enumerable (unlike sequential integers, they leak no counts — a
    hard requirement for minor privacy, DIA-001 §4.2), and index-friendly.
    Compared and hashed by value.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        _ensure_uuid7(self.value, error=InvalidParticipantIdError, label="ParticipantId")

    @classmethod
    def generate(cls) -> ParticipantId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ParticipantId:
        """Build a ``ParticipantId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ParticipantId:
        """Parse a canonical UUID string into a ``ParticipantId``."""
        return cls(_parse_uuid(value, error=InvalidParticipantIdError, label="ParticipantId"))

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses (API-000 §23)."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ParticipantId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class GuardianId:
    """A by-identity reference to a guardian (DATA-001 §4.2).

    A guardian is an adult :mod:`~apps.identity` account acting for participants;
    this context references it only by its UUID v7 identity, never by reaching into
    the Identity model (ARCH-001 §9.2).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        _ensure_uuid7(self.value, error=InvalidGuardianIdError, label="GuardianId")

    @classmethod
    def generate(cls) -> GuardianId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> GuardianId:
        """Build a ``GuardianId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> GuardianId:
        """Parse a canonical UUID string into a ``GuardianId``."""
        return cls(_parse_uuid(value, error=InvalidGuardianIdError, label="GuardianId"))

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"GuardianId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class TeacherId:
    """A by-identity reference to a teacher (DATA-001 §4.2, PRT-004)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        _ensure_uuid7(self.value, error=InvalidTeacherIdError, label="TeacherId")

    @classmethod
    def generate(cls) -> TeacherId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> TeacherId:
        """Build a ``TeacherId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> TeacherId:
        """Parse a canonical UUID string into a ``TeacherId``."""
        return cls(_parse_uuid(value, error=InvalidTeacherIdError, label="TeacherId"))

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TeacherId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class InstitutionId:
    """A cross-context, by-identity reference to an institution (ARCH-001 §9.2)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        _ensure_uuid7(self.value, error=InvalidInstitutionIdError, label="InstitutionId")

    @classmethod
    def generate(cls) -> InstitutionId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> InstitutionId:
        """Build an ``InstitutionId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> InstitutionId:
        """Parse a canonical UUID string into an ``InstitutionId``."""
        return cls(_parse_uuid(value, error=InvalidInstitutionIdError, label="InstitutionId"))

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"InstitutionId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# PersonName
# ---------------------------------------------------------------------------

_NAME_PART_RE: Final = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$", re.UNICODE)
_NAME_MAX_LEN: Final = 100


def _clean_name_part(value: str) -> str:
    return " ".join(value.split())


def _validate_name_part(value: str, *, field: str) -> str:
    cleaned = _clean_name_part(value)
    if not cleaned:
        raise InvalidPersonNameError(f"{field} must not be empty.")
    if len(cleaned) > _NAME_MAX_LEN:
        raise InvalidPersonNameError(f"{field} must be at most {_NAME_MAX_LEN} characters.")
    if not _NAME_PART_RE.match(cleaned):
        raise InvalidPersonNameError(
            f"{field} contains invalid characters (letters, spaces, hyphens and "
            f"apostrophes only): {value!r}."
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class PersonName:
    """A participant's name: given (first), family (last), optional middle (patronymic).

    ``middle_name`` carries the patronymic for ``ru-RU`` (DATA-001 §8 PersonName).
    Whitespace is collapsed on construction; names may contain letters, spaces,
    hyphens and apostrophes only. This is **minimized personal data** whose
    visibility is access-restricted (PRT-006); the pseudonym shown to judging is a
    separate :class:`DisplayAlias`. Compared by normalized parts.
    """

    first_name: str
    last_name: str
    middle_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "first_name", _validate_name_part(self.first_name, field="first_name")
        )
        object.__setattr__(
            self, "last_name", _validate_name_part(self.last_name, field="last_name")
        )
        if self.middle_name is not None and _clean_name_part(self.middle_name):
            object.__setattr__(
                self, "middle_name", _validate_name_part(self.middle_name, field="middle_name")
            )
        else:
            object.__setattr__(self, "middle_name", None)

    @classmethod
    def of(cls, first_name: str, last_name: str, middle_name: str | None = None) -> PersonName:
        """Rich constructor mirroring the field order."""
        return cls(first_name=first_name, last_name=last_name, middle_name=middle_name)

    @property
    def full(self) -> str:
        """Western display order: ``First [Middle] Last``."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(part for part in parts if part)

    @property
    def formal(self) -> str:
        """Eastern-Slavic display order: ``Last First [Middle]`` (ru-RU official)."""
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part)

    def short(self) -> str:
        """Given and family name only, dropping the patronymic: ``Иван Петров``."""
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.full


# ---------------------------------------------------------------------------
# DateOfBirth
# ---------------------------------------------------------------------------

_MIN_BIRTH_YEAR: Final = 1900
#: Upper sanity bound catching obvious typos; "not in the future" is enforced by
#: the aggregate against an injected ``now`` (a value object holds no clock).
_MAX_BIRTH_YEAR: Final = 2200


@dataclass(frozen=True, slots=True)
class DateOfBirth:
    """A participant's date of birth — the sole source of the derived age group (PRT-002).

    Structurally validated (a real calendar date within sane year bounds); the
    contextual "not in the future" check needs a reference instant and is enforced
    by the aggregate at creation. Age is **derived** here and never entered by
    hand (PRT-002), so :meth:`age_in_years` is the only sanctioned way to obtain a
    participant's age at a competition's reference date.
    """

    value: date

    def __post_init__(self) -> None:
        if not isinstance(self.value, date) or isinstance(self.value, datetime):
            raise InvalidDateOfBirthError("DateOfBirth must wrap a datetime.date (not a datetime).")
        if not _MIN_BIRTH_YEAR <= self.value.year <= _MAX_BIRTH_YEAR:
            raise InvalidDateOfBirthError(
                f"DateOfBirth year must be between {_MIN_BIRTH_YEAR} and {_MAX_BIRTH_YEAR}, "
                f"got {self.value.year}."
            )

    @classmethod
    def from_iso(cls, value: str) -> DateOfBirth:
        """Parse an ISO-8601 date string (``YYYY-MM-DD``)."""
        try:
            parsed = date.fromisoformat(value)
        except (ValueError, TypeError) as exc:
            raise InvalidDateOfBirthError(f"{value!r} is not a valid ISO-8601 date.") from exc
        return cls(parsed)

    def age_in_years(self, reference: date) -> int:
        """Full years of age at ``reference`` (PRT-002; never negative for valid data).

        Computes calendar age accounting for whether the birthday has occurred by
        ``reference``. A ``reference`` earlier than the birth date is a caller bug
        surfaced as :class:`InvalidDateOfBirthError`.
        """
        if reference < self.value:
            raise InvalidDateOfBirthError(
                "Reference date precedes the date of birth; cannot derive a non-negative age."
            )
        had_birthday = (reference.month, reference.day) >= (self.value.month, self.value.day)
        return reference.year - self.value.year - (0 if had_birthday else 1)

    def is_after(self, reference: date) -> bool:
        """Whether the birth date lies strictly after ``reference`` (a future birth)."""
        return self.value > reference

    def isoformat(self) -> str:
        """The canonical ``YYYY-MM-DD`` string for payloads and storage."""
        return self.value.isoformat()

    def __str__(self) -> str:
        return self.value.isoformat()


# ---------------------------------------------------------------------------
# AgeGroup
# ---------------------------------------------------------------------------

_AGE_GROUP_CODE_RE: Final = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")
_AGE_GROUP_CODE_MAX: Final = 32
_AGE_GROUP_LABEL_MAX: Final = 100


@dataclass(frozen=True, slots=True)
class AgeGroup:
    """A derived, tamper-resistant age band for fair comparison (PRT-002, DIA-001 §4.4).

    Defines a closed ``[min_age, max_age]`` interval (inclusive) with a stable
    ``code`` and a human ``label``. An age group is never entered by hand — it is
    produced by :class:`~apps.participants.domain.policies.AgeGroupPolicy` from a
    :class:`DateOfBirth` and a competition reference date — so this value object's
    job is to be a valid, comparable band and to answer :meth:`contains`.
    """

    code: str
    label: str
    min_age: int
    max_age: int

    def __post_init__(self) -> None:
        code = self.code.strip().lower()
        if not code or len(code) > _AGE_GROUP_CODE_MAX or not _AGE_GROUP_CODE_RE.match(code):
            raise ValueObjectValidationError(
                f"AgeGroup code must be a short lowercase slug, got {self.code!r}."
            )
        label = " ".join(self.label.split())
        if not label or len(label) > _AGE_GROUP_LABEL_MAX:
            raise ValueObjectValidationError("AgeGroup label must be a non-empty, bounded string.")
        if self.min_age < 0:
            raise ValueObjectValidationError(f"AgeGroup min_age must be >= 0, got {self.min_age}.")
        if self.max_age < self.min_age:
            raise ValueObjectValidationError(
                f"AgeGroup max_age ({self.max_age}) must be >= min_age ({self.min_age})."
            )
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "label", label)

    def contains(self, age: int) -> bool:
        """Whether ``age`` (full years) falls within this inclusive band."""
        return self.min_age <= age <= self.max_age

    def overlaps(self, other: AgeGroup) -> bool:
        """Whether this band shares any age with ``other`` (used to validate a set)."""
        return self.min_age <= other.max_age and other.min_age <= self.max_age

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# DisplayAlias
# ---------------------------------------------------------------------------

_ALIAS_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]*$")
_ALIAS_MIN_LEN: Final = 2
_ALIAS_MAX_LEN: Final = 64


@dataclass(frozen=True, slots=True)
class DisplayAlias:
    """The pseudonym under which a participant's work is shown to judging (JDG-006).

    Judges see this alias, never the participant's real :class:`PersonName`
    (PRT-006, ADR-0013), so it must be a bounded, non-identifying token. This value
    object enforces the *shape*; whether a specific alias accidentally leaks the
    real name is checked by
    :class:`~apps.participants.domain.policies.PseudonymizationPolicy`. Whitespace
    is collapsed; compared by value.
    """

    value: str

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())
        if not _ALIAS_MIN_LEN <= len(cleaned) <= _ALIAS_MAX_LEN:
            raise InvalidDisplayAliasError(
                f"DisplayAlias must be {_ALIAS_MIN_LEN}-{_ALIAS_MAX_LEN} characters."
            )
        if not _ALIAS_RE.match(cleaned):
            raise InvalidDisplayAliasError(
                f"DisplayAlias may contain letters, digits, spaces, hyphens and underscores "
                f"only: {self.value!r}."
            )
        object.__setattr__(self, "value", cleaned)

    @classmethod
    def from_string(cls, value: str) -> DisplayAlias:
        """Parse and normalize a display alias."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# ConsentReference
# ---------------------------------------------------------------------------

_CONSENT_VERSION_MAX: Final = 64


@dataclass(frozen=True, slots=True)
class ConsentReference:
    """A by-identity reference to the Identity consent that authorizes a minor (PRT-001).

    Consent is owned by the Identity context; this context records only the
    reference needed to know an **active, matching** consent exists before a
    participant may become active (PRT-001, APP-001). It carries the consent's UUID
    and the exact text version in force (IDN-005) — never the consent text itself.
    Compared by value.
    """

    consent_id: uuid.UUID
    consent_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.consent_id, uuid.UUID):  # defensive: wrong type
            raise InvalidConsentReferenceError("ConsentReference.consent_id must be a uuid.UUID.")
        version = self.consent_version.strip()
        if not version or len(version) > _CONSENT_VERSION_MAX:
            raise InvalidConsentReferenceError(
                "ConsentReference.consent_version must be non-empty."
            )
        object.__setattr__(self, "consent_version", version)

    @classmethod
    def of(cls, consent_id: str | uuid.UUID, consent_version: str) -> ConsentReference:
        """Build from a raw id (string or UUID) and a version string."""
        if isinstance(consent_id, uuid.UUID):
            parsed = consent_id
        else:
            parsed = _parse_uuid(
                consent_id, error=InvalidConsentReferenceError, label="ConsentReference"
            )
        return cls(consent_id=parsed, consent_version=consent_version)

    def __str__(self) -> str:
        return f"{self.consent_id}@{self.consent_version}"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ParticipantStatus(StrEnum):
    """The lifecycle state of the Participant aggregate (DATA-004 §4.3).

    ``Created → Verified → Active → Archived → Erased``, with ``Archived`` allowing
    reactivation back to ``Active`` and ``Erased`` terminal and irreversible. A
    :class:`~enum.StrEnum`, so each member *is* its wire/storage value.
    """

    CREATED = "created"
    VERIFIED = "verified"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERASED = "erased"


class RelationshipStatus(StrEnum):
    """The lifecycle state of a guardian relationship (DATA-001 §4.2).

    ``Proposed → Active → Revoked``. Verifying a proposed link makes it ``Active``
    (a verified, effective guardian relationship, DATA-001 §4.2 "Verified↓Active"),
    which is what PRT-001 requires before a participant may be activated.
    """

    PROPOSED = "proposed"
    ACTIVE = "active"
    REVOKED = "revoked"


class GuardianRelationshipType(StrEnum):
    """The kind of guardian↔participant relationship (DATA-001 §4.2 relationship type)."""

    MOTHER = "mother"
    FATHER = "father"
    LEGAL_GUARDIAN = "legal_guardian"
    OTHER = "other"


class ActorType(StrEnum):
    """Whether the adult acting for a participant is a guardian or a teacher (DATA-001 §4.2)."""

    GUARDIAN = "guardian"
    TEACHER = "teacher"


# ---------------------------------------------------------------------------
# ActorReference
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActorReference:
    """The verified adult who created/acts for a participant (DATA-001 §4.2, IDN-004).

    Children never hold independent accounts (IDN-004); a participant is always
    created by a verified guardian or an authorized teacher. This value object
    records that actor by identity and kind, so the creator is captured on
    :class:`~apps.participants.domain.events.ParticipantCreated` for the audit trail.
    """

    actor_id: uuid.UUID
    actor_type: ActorType

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, uuid.UUID):  # defensive: wrong type
            raise ValueObjectValidationError("ActorReference.actor_id must be a uuid.UUID.")

    @classmethod
    def of(cls, actor_id: str | uuid.UUID, actor_type: ActorType) -> ActorReference:
        """Build from a raw id (string or UUID) and an :class:`ActorType`."""
        parsed = actor_id if isinstance(actor_id, uuid.UUID) else _parse_uuid(actor_id, error=ValueObjectValidationError, label="ActorReference")
        return cls(actor_id=parsed, actor_type=actor_type)

    def __str__(self) -> str:
        return f"{self.actor_type.value}:{self.actor_id}"


# ---------------------------------------------------------------------------
# GuardianLink (relationship inside the Participant aggregate)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GuardianLink:
    """A guardian↔participant relationship held inside the Participant aggregate.

    Realizes GUARDIAN_RELATIONSHIP (DIA-001 §4.2), whose aggregate root is the
    participant. Modeled as an **immutable** value object: a state change produces
    a *new* link (:meth:`verified`, :meth:`revoked`) rather than mutating in place,
    keeping the aggregate the sole author of transitions. Identified within the
    aggregate by :attr:`guardian_id`.
    """

    guardian_id: GuardianId
    relationship_type: GuardianRelationshipType
    status: RelationshipStatus = RelationshipStatus.PROPOSED
    established_at: datetime | None = None

    def is_active(self) -> bool:
        """Whether this is a verified, effective relationship (PRT-001)."""
        return self.status is RelationshipStatus.ACTIVE

    def is_proposed(self) -> bool:
        """Whether this relationship is still awaiting verification."""
        return self.status is RelationshipStatus.PROPOSED

    def is_revoked(self) -> bool:
        """Whether this relationship has been revoked."""
        return self.status is RelationshipStatus.REVOKED

    def verified(self, *, now: datetime) -> GuardianLink:
        """Return the same link promoted to ``Active`` and stamped at ``now``."""
        return replace(self, status=RelationshipStatus.ACTIVE, established_at=now)

    def revoked(self) -> GuardianLink:
        """Return the same link with its status set to ``Revoked``."""
        return replace(self, status=RelationshipStatus.REVOKED)


# ---------------------------------------------------------------------------
# InstitutionAuthority
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstitutionAuthority:
    """An authorizing institution (and optional teacher) for a participant (PRT-001, PRT-004).

    The alternative to guardian relationships for the activation precondition:
    a participant may become active under a verified guardian **or** an authorized
    institution/teacher link with recorded consent (PRT-001). The teacher, when
    present, acts only within this institution (PRT-004).
    """

    institution_id: InstitutionId
    teacher_id: TeacherId | None = None
