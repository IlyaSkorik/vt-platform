"""Value objects for the Competitions bounded context.

Immutable, identity-less concepts of the Competition domain. Each is a frozen,
slotted dataclass that validates on construction, compares by value, and can
never be mutated. **Pure domain code** (ARCH-001 §4.1, §7.2): standard library
only — no Django, no ORM, no third-party validators.

Value objects implemented here fall into five groups:

* **Identifiers** (UUID v7, one distinct type per aggregate/child/reference):
  :class:`CompetitionId`, :class:`CategoryId`, :class:`DisciplineId`,
  :class:`AgeCategoryId`, :class:`ParticipantGroupId`,
  :class:`ParticipationFormatId`, :class:`RegulationId`, :class:`DocumentId`,
  and :class:`OrganizerId` (an opaque reference to the Organization context,
  held by id only — no cross-context import edge).
* **General-information VOs**: :class:`CompetitionTitle`,
  :class:`CompetitionDescription`, :class:`Season`, :class:`Venue`,
  :class:`FileReference` (logo/banner/regulation/document files),
  :class:`DateRange` (registration & competition periods).
* **Configuration ranges & names**: :class:`AgeRange`,
  :class:`ParticipantCountRange`, :class:`CategoryName`, :class:`DisciplineName`,
  :class:`ParticipantGroupName`, :class:`ParticipationFormatName`,
  :class:`ParticipationFormatDescription`, :class:`RegulationTitle`,
  :class:`RegulationVersion`, :class:`DocumentTitle`, :class:`DocumentDescription`.
* **Enumerations**: :class:`CompetitionStatus`, :class:`DocumentCategory`,
  :class:`DocumentVisibility`, :class:`Currency`.
* **Pricing & admissibility**: :class:`Money`, :class:`AdmissionCombination`
  (the five-dimensional key shared by admission and pricing), :class:`AdmissionRule`
  and :class:`PricingRule` (immutable configuration facts, held in sets on the root).

The id value objects intentionally duplicate the UUID-v7 logic that also exists
in the Identity and Organization contexts: the bounded contexts stay independent
(no shared import edge), so a little duplication is preferred over a cross-context
dependency (ARCH-001 §14).
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from .exceptions import (
    InvalidAgeCategoryIdError,
    InvalidAgeCategoryNameError,
    InvalidAgeRangeError,
    InvalidCategoryDescriptionError,
    InvalidParticipantGroupDescriptionError,
    InvalidCategoryIdError,
    InvalidCategoryNameError,
    InvalidCompetitionDescriptionError,
    InvalidCompetitionIdError,
    InvalidCompetitionTitleError,
    InvalidContactIdError,
    InvalidContactValueError,
    InvalidDateRangeError,
    InvalidDisciplineIdError,
    InvalidDisciplineNameError,
    InvalidDocumentDescriptionError,
    InvalidDocumentIdError,
    InvalidDocumentTitleError,
    InvalidFileReferenceError,
    InvalidInformationBlockIdError,
    InvalidInformationBlockTitleError,
    InvalidMoneyError,
    InvalidOrganizerIdError,
    InvalidParticipantCountRangeError,
    InvalidParticipantGroupIdError,
    InvalidParticipantGroupNameError,
    InvalidParticipationFormatDescriptionError,
    InvalidParticipationFormatIdError,
    InvalidParticipationFormatNameError,
    InvalidRegistrationDeadlinesError,
    InvalidRegulationIdError,
    InvalidRegulationTitleError,
    InvalidRegulationVersionError,
    InvalidRichTextError,
    InvalidSeasonError,
    InvalidServiceDescriptionError,
    InvalidServiceIdError,
    InvalidServiceNameError,
    InvalidTemplateIdError,
    InvalidTemplateNameError,
    InvalidVenueError,
)

__all__ = [
    "AdmissionCombination",
    "AdmissionRule",
    "AgeCategoryId",
    "AgeCategoryName",
    "AgeCategoryType",
    "AgeRange",
    "CategoryDescription",
    "CategoryId",
    "CategoryName",
    "CompetitionBranding",
    "CompetitionDescription",
    "CompetitionId",
    "CompetitionPublicationReport",
    "CompetitionSettings",
    "CompetitionStatus",
    "CompetitionTitle",
    "ContactId",
    "ContactType",
    "ContactValue",
    "Currency",
    "DateRange",
    "DeadlineKind",
    "DisciplineId",
    "DisciplineName",
    "DocumentCategory",
    "DocumentDescription",
    "DocumentId",
    "DocumentTitle",
    "DocumentVisibility",
    "FileReference",
    "InformationBlockId",
    "InformationBlockTitle",
    "MixedAgeCalculationMethod",
    "Money",
    "OrganizerId",
    "ParticipantCountRange",
    "ParticipantGroupDescription",
    "ParticipantGroupId",
    "ParticipantGroupName",
    "ParticipationFormatDescription",
    "ParticipationFormatId",
    "ParticipationFormatName",
    "PricingCalculationType",
    "PricingRule",
    "PublicationIssue",
    "PublicationIssueCode",
    "RegistrationDeadlines",
    "RegulationId",
    "RegulationTitle",
    "RegulationVersion",
    "RichText",
    "RichTextFormat",
    "Season",
    "ServiceDescription",
    "ServiceId",
    "ServiceName",
    "TemplateId",
    "TemplateName",
    "Venue",
]

_UUID_V7_VERSION: Final = 7


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7.

    Implemented directly rather than via ``uuid.uuid7`` (added only in Python
    3.14) so the domain works on any supported interpreter. The time-ordered
    layout keeps primary keys roughly monotonic, avoiding the index fragmentation
    random UUID v4 keys cause at scale.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


# ---------------------------------------------------------------------------
# Identifiers (UUID v7, one distinct type per aggregate/child/reference)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class CompetitionId:
    """The globally unique identity of a :class:`Competition` aggregate (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidCompetitionIdError(f"CompetitionId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidCompetitionIdError(f"CompetitionId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> CompetitionId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> CompetitionId:
        """Build a ``CompetitionId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> CompetitionId:
        """Parse a canonical UUID string, or raise :class:`InvalidCompetitionIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCompetitionIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"CompetitionId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class CategoryId:
    """The identity of a :class:`Category` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidCategoryIdError(f"CategoryId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidCategoryIdError(f"CategoryId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> CategoryId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> CategoryId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> CategoryId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCategoryIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"CategoryId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class DisciplineId:
    """The identity of a :class:`Discipline` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidDisciplineIdError(f"DisciplineId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidDisciplineIdError(f"DisciplineId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> DisciplineId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> DisciplineId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> DisciplineId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidDisciplineIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"DisciplineId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class AgeCategoryId:
    """The identity of an :class:`AgeCategory` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidAgeCategoryIdError(f"AgeCategoryId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidAgeCategoryIdError(f"AgeCategoryId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> AgeCategoryId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> AgeCategoryId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> AgeCategoryId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidAgeCategoryIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"AgeCategoryId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ParticipantGroupId:
    """The identity of a :class:`ParticipantGroup` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidParticipantGroupIdError(f"ParticipantGroupId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidParticipantGroupIdError(f"ParticipantGroupId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ParticipantGroupId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ParticipantGroupId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ParticipantGroupId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidParticipantGroupIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ParticipantGroupId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ParticipationFormatId:
    """The identity of a :class:`ParticipationFormat` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidParticipationFormatIdError(f"ParticipationFormatId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidParticipationFormatIdError(f"ParticipationFormatId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ParticipationFormatId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ParticipationFormatId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ParticipationFormatId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidParticipationFormatIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ParticipationFormatId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class RegulationId:
    """The identity of a :class:`CompetitionRegulation` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidRegulationIdError(f"RegulationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidRegulationIdError(f"RegulationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> RegulationId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> RegulationId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> RegulationId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidRegulationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"RegulationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class DocumentId:
    """The identity of a :class:`CompetitionDocument` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidDocumentIdError(f"DocumentId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidDocumentIdError(f"DocumentId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> DocumentId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> DocumentId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> DocumentId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidDocumentIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"DocumentId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class OrganizerId:
    """A reference to the organizing party, held only as an opaque UUID v7.

    The Competitions context never resolves this to an Organization aggregate — it
    knows the organizer solely by this id. Deliberately a **separate** type from
    the Organization context's own ids so the two contexts share no import edge
    (ARCH-001 §14).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidOrganizerIdError(f"OrganizerId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidOrganizerIdError(f"OrganizerId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> OrganizerId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> OrganizerId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidOrganizerIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OrganizerId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class TemplateId:
    """The identity of a :class:`CompetitionTemplate` aggregate (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidTemplateIdError(f"TemplateId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidTemplateIdError(f"TemplateId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> TemplateId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> TemplateId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> TemplateId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidTemplateIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TemplateId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ServiceId:
    """The identity of an :class:`AdditionalService` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidServiceIdError(f"ServiceId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidServiceIdError(f"ServiceId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ServiceId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ServiceId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ServiceId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidServiceIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ServiceId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ContactId:
    """The identity of a :class:`Contact` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidContactIdError(f"ContactId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidContactIdError(f"ContactId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ContactId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ContactId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ContactId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidContactIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ContactId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class InformationBlockId:
    """The identity of an :class:`InformationBlock` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidInformationBlockIdError(f"InformationBlockId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidInformationBlockIdError(f"InformationBlockId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> InformationBlockId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> InformationBlockId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> InformationBlockId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidInformationBlockIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"InformationBlockId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# General-information value objects
# ---------------------------------------------------------------------------

_TITLE_MAX: Final = 200
_DESCRIPTION_MAX: Final = 5_000
_SEASON_MAX: Final = 50
_VENUE_NAME_MAX: Final = 200
_VENUE_ADDRESS_MAX: Final = 500
_FILE_REFERENCE_MAX: Final = 1_024


@dataclass(frozen=True, slots=True)
class CompetitionTitle:
    """A non-empty, length-bounded competition title."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidCompetitionTitleError("Competition title must not be empty.")
        if len(stripped) > _TITLE_MAX:
            raise InvalidCompetitionTitleError(f"Competition title must be at most {_TITLE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CompetitionDescription:
    """A length-bounded competition description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _DESCRIPTION_MAX:
            raise InvalidCompetitionDescriptionError(f"Competition description must be at most {_DESCRIPTION_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Season:
    """A competition season label (e.g. ``"2025/2026"``)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidSeasonError("Season must not be empty.")
        if len(stripped) > _SEASON_MAX:
            raise InvalidSeasonError(f"Season must be at most {_SEASON_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Venue:
    """The physical location of a competition — a display name and optional address."""

    name: str
    address: str | None = None

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise InvalidVenueError("Venue name must not be empty.")
        if len(name) > _VENUE_NAME_MAX:
            raise InvalidVenueError(f"Venue name must be at most {_VENUE_NAME_MAX} characters.")
        object.__setattr__(self, "name", name)
        if self.address is not None:
            address = self.address.strip()
            if not address:
                object.__setattr__(self, "address", None)
            elif len(address) > _VENUE_ADDRESS_MAX:
                raise InvalidVenueError(f"Venue address must be at most {_VENUE_ADDRESS_MAX} characters.")
            else:
                object.__setattr__(self, "address", address)

    def __str__(self) -> str:
        return self.name if self.address is None else f"{self.name}, {self.address}"


@dataclass(frozen=True, slots=True)
class FileReference:
    """An opaque reference to a stored file (a storage key or URL).

    The domain treats it as an opaque, length-bounded token: it neither knows nor
    cares whether it is an S3 key, a CDN URL, or a local path — resolving it to
    bytes is an infrastructure concern. Used for the competition logo/banner and
    for regulation and document files.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidFileReferenceError("File reference must not be empty.")
        if len(stripped) > _FILE_REFERENCE_MAX:
            raise InvalidFileReferenceError(f"File reference must be at most {_FILE_REFERENCE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DateRange:
    """An inclusive range of calendar dates (start ≤ end).

    Models both the registration period and the competition period. Calendar dates
    (not instants) keep the model timezone-free; a finer-grained window is a future
    extension point.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise InvalidDateRangeError("DateRange bounds must be datetime.date instances.")
        if self.end < self.start:
            raise InvalidDateRangeError(f"DateRange end {self.end} must not precede start {self.start}.")

    def contains(self, moment: date) -> bool:
        """Whether ``moment`` falls within the inclusive range."""
        return self.start <= moment <= self.end

    def overlaps(self, other: DateRange) -> bool:
        """Whether this range shares at least one day with ``other``."""
        return self.start <= other.end and other.start <= self.end

    def __str__(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"


# ---------------------------------------------------------------------------
# Configuration ranges & names
# ---------------------------------------------------------------------------

_AGE_MIN: Final = 0
_AGE_MAX: Final = 120
_NAME_MAX: Final = 120
_REGULATION_TITLE_MAX: Final = 200
_REGULATION_VERSION_MAX: Final = 50
_DOCUMENT_TITLE_MAX: Final = 200
_CATEGORY_DESCRIPTION_MAX: Final = 2_000
_DOCUMENT_DESCRIPTION_MAX: Final = 2_000


@dataclass(frozen=True, slots=True)
class AgeRange:
    """An inclusive age band (e.g. ``3-5``), configured per competition."""

    min_age: int
    max_age: int

    def __post_init__(self) -> None:
        if not isinstance(self.min_age, int) or not isinstance(self.max_age, int):
            raise InvalidAgeRangeError("Age bounds must be integers.")
        if not (_AGE_MIN <= self.min_age <= _AGE_MAX):
            raise InvalidAgeRangeError(f"Minimum age must be between {_AGE_MIN} and {_AGE_MAX}, got {self.min_age}.")
        if not (_AGE_MIN <= self.max_age <= _AGE_MAX):
            raise InvalidAgeRangeError(f"Maximum age must be between {_AGE_MIN} and {_AGE_MAX}, got {self.max_age}.")
        if self.max_age < self.min_age:
            raise InvalidAgeRangeError(f"Maximum age {self.max_age} must not be less than minimum age {self.min_age}.")

    def contains(self, age: int) -> bool:
        """Whether ``age`` falls within the inclusive band."""
        return self.min_age <= age <= self.max_age

    def overlaps(self, other: AgeRange) -> bool:
        """Whether this band shares at least one age with ``other``."""
        return self.min_age <= other.max_age and other.min_age <= self.max_age

    def __str__(self) -> str:
        return f"{self.min_age}-{self.max_age}"


@dataclass(frozen=True, slots=True)
class ParticipantCountRange:
    """A participant-count band underpinning a group (e.g. Solo=1, Ensemble=3-5, Choir=6+).

    ``max_count`` is ``None`` for an open-ended upper bound (the ``6+`` case).
    """

    min_count: int
    max_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.min_count, int):
            raise InvalidParticipantCountRangeError("Minimum participant count must be an integer.")
        if self.min_count < 1:
            raise InvalidParticipantCountRangeError(f"Minimum participant count must be at least 1, got {self.min_count}.")
        if self.max_count is not None:
            if not isinstance(self.max_count, int):
                raise InvalidParticipantCountRangeError("Maximum participant count must be an integer or None.")
            if self.max_count < self.min_count:
                raise InvalidParticipantCountRangeError(f"Maximum participant count {self.max_count} must not be less than minimum {self.min_count}.")

    @property
    def is_open_ended(self) -> bool:
        """Whether the band has no upper bound (e.g. ``6+``)."""
        return self.max_count is None

    def contains(self, count: int) -> bool:
        """Whether a group of ``count`` participants falls in this band."""
        if count < self.min_count:
            return False
        return self.max_count is None or count <= self.max_count

    def overlaps(self, other: ParticipantCountRange) -> bool:
        """Whether this band shares at least one count with ``other``."""
        this_max = self.max_count if self.max_count is not None else float("inf")
        other_max = other.max_count if other.max_count is not None else float("inf")
        return self.min_count <= other_max and other.min_count <= this_max

    def __str__(self) -> str:
        return f"{self.min_count}+" if self.max_count is None else f"{self.min_count}-{self.max_count}"


def _validate_name(value: str, *, error: type[Exception], label: str, maximum: int) -> str:
    stripped = value.strip()
    if not stripped:
        raise error(f"{label} must not be empty.")
    if len(stripped) > maximum:
        raise error(f"{label} must be at most {maximum} characters.")
    return stripped


@dataclass(frozen=True, slots=True)
class CategoryName:
    """A non-empty, length-bounded competition-category name (e.g. "Vocal", "Choreography")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_name(self.value, error=InvalidCategoryNameError, label="Category name", maximum=_NAME_MAX))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CategoryDescription:
    """A length-bounded category description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _CATEGORY_DESCRIPTION_MAX:
            raise InvalidCategoryDescriptionError(f"Category description must be at most {_CATEGORY_DESCRIPTION_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AgeCategoryName:
    """A non-empty, length-bounded age-category name (e.g. "Juniors", "3-5")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _validate_name(self.value, error=InvalidAgeCategoryNameError, label="Age category name", maximum=_NAME_MAX)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DisciplineName:
    """A non-empty, length-bounded discipline name (e.g. "Pop", "Folk", "Academic")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_name(self.value, error=InvalidDisciplineNameError, label="Discipline name", maximum=_NAME_MAX))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ParticipantGroupName:
    """A non-empty, length-bounded participant-group name (e.g. "Solo", "Choir")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _validate_name(self.value, error=InvalidParticipantGroupNameError, label="Participant group name", maximum=_NAME_MAX)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ParticipantGroupDescription:
    """A length-bounded participant-group description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _CATEGORY_DESCRIPTION_MAX:
            raise InvalidParticipantGroupDescriptionError(
                f"Participant group description must be at most {_CATEGORY_DESCRIPTION_MAX} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ParticipationFormatName:
    """A non-empty, length-bounded participation-format name (e.g. "Очно", "Онлайн")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_name(self.value, error=InvalidParticipationFormatNameError, label="Participation format name", maximum=_NAME_MAX),
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ParticipationFormatDescription:
    """A length-bounded participation-format description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _CATEGORY_DESCRIPTION_MAX:
            raise InvalidParticipationFormatDescriptionError(
                f"Participation format description must be at most {_CATEGORY_DESCRIPTION_MAX} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RegulationTitle:
    """A non-empty, length-bounded regulation title."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _validate_name(self.value, error=InvalidRegulationTitleError, label="Regulation title", maximum=_REGULATION_TITLE_MAX)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RegulationVersion:
    """A regulation version label (e.g. ``"1.0"``, ``"2025.1"``)."""

    value: str

    def __post_init__(self) -> None:
        validated = _validate_name(self.value, error=InvalidRegulationVersionError, label="Regulation version", maximum=_REGULATION_VERSION_MAX)
        object.__setattr__(self, "value", validated)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DocumentTitle:
    """A non-empty, length-bounded document title."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _validate_name(self.value, error=InvalidDocumentTitleError, label="Document title", maximum=_DOCUMENT_TITLE_MAX)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DocumentDescription:
    """A length-bounded document description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _DOCUMENT_DESCRIPTION_MAX:
            raise InvalidDocumentDescriptionError(f"Document description must be at most {_DOCUMENT_DESCRIPTION_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TemplateName:
    """A non-empty, length-bounded competition-template name."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_name(self.value, error=InvalidTemplateNameError, label="Template name", maximum=_TITLE_MAX))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ServiceName:
    """A non-empty, length-bounded additional-service name (e.g. "Medal", "Video recording")."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_name(self.value, error=InvalidServiceNameError, label="Service name", maximum=_NAME_MAX))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ServiceDescription:
    """A length-bounded additional-service description (may be blank)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > _DOCUMENT_DESCRIPTION_MAX:
            raise InvalidServiceDescriptionError(f"Service description must be at most {_DOCUMENT_DESCRIPTION_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class CompetitionStatus(StrEnum):
    """The competition's lifecycle state.

    ``DRAFT``               — configurator open; configuration is mutable.
    ``CONFIGURED``          — organizer has signalled configuration is done; still editable.
    ``READY``               — configuration validated as publishable; frozen (edit by reverting).
    ``PUBLISHED``           — open to applicants; configuration frozen.
    ``REGISTRATION_OPEN``   — accepting applications.
    ``REGISTRATION_CLOSED`` — application window closed.
    ``RUNNING``             — the competition is taking place.
    ``COMPLETED``           — the competition has finished.
    ``ARCHIVED``            — retired; immutable and read-only.

    Legal transitions are enforced by the :class:`~apps.competitions.domain.entities.
    Competition` aggregate; this enum only names the states.
    """

    DRAFT = "DRAFT"
    CONFIGURED = "CONFIGURED"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class DocumentCategory(StrEnum):
    """The organizer-facing classification of an uploaded document.

    ``OTHER`` is the catch-all for arbitrary additional files. Note this differs
    from a competition *category* (:class:`CategoryName`): this is a fixed
    vocabulary for filing documents, not the configurable discipline taxonomy.
    """

    REGULATION = "REGULATION"
    PROGRAM = "PROGRAM"
    SCHEDULE = "SCHEDULE"
    REQUISITES = "REQUISITES"
    MEMO = "MEMO"
    ACCOMMODATION = "ACCOMMODATION"
    OTHER = "OTHER"


class DocumentVisibility(StrEnum):
    """Who may see a competition document.

    ``ALL``          — everyone, including anonymous visitors.
    ``PUBLIC``       — shown on the public competition page.
    ``PARTICIPANTS`` — only registered participants.
    ``STAFF``        — only organization staff (internal).
    """

    ALL = "ALL"
    PUBLIC = "PUBLIC"
    PARTICIPANTS = "PARTICIPANTS"
    STAFF = "STAFF"


class AgeCategoryType(StrEnum):
    """Whether an age category applies to a single standard age band or a mixed group."""

    STANDARD = "STANDARD"
    MIXED = "MIXED"


class MixedAgeCalculationMethod(StrEnum):
    """How the age of a mixed-age group is calculated for placement purposes."""

    AVERAGE = "AVERAGE"
    OLDEST = "OLDEST"
    YOUNGEST = "YOUNGEST"


class Currency(StrEnum):
    """An ISO-4217 currency code a price is denominated in (default ``BYN``)."""

    BYN = "BYN"


class PricingCalculationType(StrEnum):
    """How a pricing rule's unit amount becomes an application total.

    ``PER_PARTICIPANT`` — total = unit price × participant count.
    ``PER_PERFORMANCE`` — total = unit price (fixed), independent of headcount.
    Applies to every participation format.
    """

    PER_PARTICIPANT = "PER_PARTICIPANT"
    PER_PERFORMANCE = "PER_PERFORMANCE"


# ---------------------------------------------------------------------------
# Pricing & admissibility
# ---------------------------------------------------------------------------

_MONEY_QUANTUM: Final = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """A non-negative monetary amount in a single currency, quantized to 2 dp.

    In this context a :class:`Money` is a per-participant price or a fixed service
    price. Amounts are stored as :class:`~decimal.Decimal` to avoid binary-float
    rounding error.

    **Future extension points (not implemented):** multiple currencies already fit
    (``Currency`` is an enum), but *regional pricing* (price varying by region) and
    *tax calculation* (net/gross, VAT) would layer on top — most naturally as a
    ``TaxedMoney`` / ``PriceBreakdown`` value object and a pricing policy, leaving
    this primitive untouched.
    """

    amount: Decimal
    currency: Currency = Currency.BYN

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise InvalidMoneyError(f"Money amount must be a decimal.Decimal, got {type(self.amount)!r}.")
        if not isinstance(self.currency, Currency):
            raise InvalidMoneyError(f"Money currency must be a Currency, got {type(self.currency)!r}.")
        if not self.amount.is_finite():
            raise InvalidMoneyError("Money amount must be a finite number.")
        if self.amount < 0:
            raise InvalidMoneyError(f"Money amount must not be negative, got {self.amount}.")
        try:
            quantized = self.amount.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:  # e.g. more precision than the quantum allows unexpectedly
            raise InvalidMoneyError(f"Money amount {self.amount} cannot be represented with 2 decimal places.") from exc
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def of(cls, amount: str | int | Decimal, currency: Currency = Currency.BYN) -> Money:
        """Build :class:`Money` from a string/int/Decimal amount (never a float)."""
        if isinstance(amount, float):
            raise InvalidMoneyError("Refusing to build Money from a float; pass a str, int, or Decimal.")
        try:
            decimal_amount = Decimal(amount)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidMoneyError(f"{amount!r} is not a valid monetary amount.") from exc
        return cls(amount=decimal_amount, currency=currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.value}"


@dataclass(frozen=True, slots=True)
class AdmissionCombination:
    """The five-dimensional key that identifies one admissible configuration.

    The shared vocabulary of both :class:`AdmissionRule` and :class:`PricingRule`
    (and, in a future iteration, of an Application): *what* discipline, in *which*
    category, for *which* age band and participant group, in *which* participation
    format. Referenced elements are held by id; the aggregate root validates that
    each id resolves and is mutually consistent before a rule using this key is
    accepted.
    """

    category_id: CategoryId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId

    def __str__(self) -> str:
        return (
            f"{self.category_id}/{self.discipline_id}/{self.age_category_id}/"
            f"{self.participant_group_id}/{self.participation_format_id}"
        )


@dataclass(frozen=True, slots=True)
class AdmissionRule:
    """An allowed combination: an application may be created only for a combination a rule covers.

    Modelled as an immutable configuration *fact* (a value object), not an entity:
    it has no identity or lifecycle of its own beyond the combination it names, so
    the aggregate holds a set of them and "editing" means remove-then-add. The
    thin wrapper (rather than a bare :class:`AdmissionCombination`) is a
    deliberate extension point — per-rule attributes such as quotas or deadlines
    can be added here later without touching call sites.
    """

    combination: AdmissionCombination

    def __str__(self) -> str:
        return f"AdmissionRule({self.combination})"


@dataclass(frozen=True, slots=True)
class PricingRule:
    """The list price for one admissible combination.

    The ``price_per_participant`` field holds the configured unit amount. How that
    amount becomes an application total is governed by ``calculation_type``:

    * :attr:`PricingCalculationType.PER_PARTICIPANT` — total = unit × headcount
    * :attr:`PricingCalculationType.PER_PERFORMANCE` — total = unit (fixed)

    Offline/online (and any other format) differ naturally because
    ``participation_format_id`` is part of the combination. Like
    :class:`AdmissionRule` this is an immutable configuration fact keyed by its
    combination.

    **Future extension points (not implemented):** *promo codes*, *discounts* and
    *coupons* are deliberately absent — they belong to a pricing/checkout stage
    (likely the future Applications/Payments contexts), computed *from* this base
    price rather than stored on it.
    """

    combination: AdmissionCombination
    price_per_participant: Money
    calculation_type: PricingCalculationType = PricingCalculationType.PER_PARTICIPANT

    def total_for(self, participant_count: int) -> Money:
        """Compute the application total for ``participant_count`` participants."""
        if participant_count < 1:
            raise InvalidMoneyError("Participant count must be at least 1 to compute a total.")
        if self.calculation_type is PricingCalculationType.PER_PERFORMANCE:
            return self.price_per_participant
        return Money.of(
            self.price_per_participant.amount * participant_count,
            self.price_per_participant.currency,
        )

    def __str__(self) -> str:
        return (
            f"PricingRule({self.combination} @ {self.price_per_participant} "
            f"[{self.calculation_type.value}])"
        )


# ---------------------------------------------------------------------------
# Publication readiness report
# ---------------------------------------------------------------------------


class PublicationIssueCode(StrEnum):
    """A machine-readable code for a publication-readiness finding.

    Codes let the presentation edge localize/route findings without parsing the
    human-readable ``message``. ``ERROR``-level codes block publication;
    ``WARNING``-level codes do not.
    """

    NO_CATEGORIES = "NO_CATEGORIES"
    NO_DISCIPLINES = "NO_DISCIPLINES"
    NO_AGE_CATEGORIES = "NO_AGE_CATEGORIES"
    NO_PARTICIPANT_GROUPS = "NO_PARTICIPANT_GROUPS"
    NO_PARTICIPATION_FORMATS = "NO_PARTICIPATION_FORMATS"
    NO_ADMISSION_RULES = "NO_ADMISSION_RULES"
    MISSING_PRICING_RULES = "MISSING_PRICING_RULES"
    MISSING_REGULATION = "MISSING_REGULATION"
    UNUSED_PARTICIPATION_FORMAT = "UNUSED_PARTICIPATION_FORMAT"


@dataclass(frozen=True, slots=True)
class PublicationIssue:
    """A single finding in a :class:`CompetitionPublicationReport`."""

    code: PublicationIssueCode
    message: str

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"


@dataclass(frozen=True, slots=True)
class CompetitionPublicationReport:
    """A structured verdict on whether a competition can be published.

    Replaces a bare boolean: it distinguishes blocking ``errors`` (which must be
    resolved before publication) from advisory ``warnings`` (recommended, not
    required). ``is_publishable`` is derived — it is true exactly when there are no
    errors, regardless of warnings.
    """

    errors: tuple[PublicationIssue, ...] = ()
    warnings: tuple[PublicationIssue, ...] = ()

    @property
    def is_publishable(self) -> bool:
        """True when nothing blocks publication (there may still be warnings)."""
        return not self.errors

    def error_summary(self) -> str:
        """A single-line, semicolon-joined summary of the blocking errors."""
        return "; ".join(issue.message for issue in self.errors)


# ---------------------------------------------------------------------------
# Rich text
# ---------------------------------------------------------------------------

_RICH_TEXT_MAX: Final = 50_000


class RichTextFormat(StrEnum):
    """A declared, uninterpreted markup flavour for :class:`RichText`.

    The domain **stores** this tag but never parses or renders content — rendering
    and sanitisation are presentation concerns. Adding a flavour (e.g. Portable
    Text) is the extension point for richer editors.
    """

    PLAIN = "PLAIN"
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"


@dataclass(frozen=True, slots=True, repr=False)
class RichText:
    """Storage-agnostic rich textual content — a length-bounded string plus a format tag.

    A dedicated value object (rather than a bare ``str``) so large informational
    content is never confused with a short label, and so a declared :class:`RichTextFormat`
    travels with the text. The domain makes **no HTML/markdown assumptions** and runs
    **no parser**: it neither validates the body against ``format`` nor renders it.
    """

    value: str
    format: RichTextFormat = RichTextFormat.PLAIN

    def __post_init__(self) -> None:
        if len(self.value) > _RICH_TEXT_MAX:
            raise InvalidRichTextError(f"Rich text must be at most {_RICH_TEXT_MAX} characters.")

    @property
    def is_empty(self) -> bool:
        return not self.value.strip()

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        preview = self.value[:24] + "…" if len(self.value) > 24 else self.value
        return f"RichText(format={self.format.value}, value={preview!r})"


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

_CONTACT_VALUE_MAX: Final = 500
_INFORMATION_BLOCK_TITLE_MAX: Final = 200


class ContactType(StrEnum):
    """A channel an official competition contact is reachable through.

    Deliberately a fixed vocabulary of the channels used today; new channels are
    added here. Per-channel value validation (phone vs URL vs handle) is a future
    extension — today the domain stores the value as an opaque bounded string.
    """

    PHONE = "PHONE"
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    WHATSAPP = "WHATSAPP"
    WEBSITE = "WEBSITE"
    VK = "VK"
    INSTAGRAM = "INSTAGRAM"


@dataclass(frozen=True, slots=True)
class ContactValue:
    """A non-empty, length-bounded contact value (phone number, address, URL, handle).

    Opaque to the domain: it is not validated against the :class:`ContactType`
    (that is a future, channel-specific extension), only bounded and non-empty.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidContactValueError("Contact value must not be empty.")
        if len(stripped) > _CONTACT_VALUE_MAX:
            raise InvalidContactValueError(f"Contact value must be at most {_CONTACT_VALUE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class InformationBlockTitle:
    """A non-empty, length-bounded title of a public-information block."""

    value: str

    def __post_init__(self) -> None:
        validated = _validate_name(
            self.value, error=InvalidInformationBlockTitleError, label="Information block title", maximum=_INFORMATION_BLOCK_TITLE_MAX
        )
        object.__setattr__(self, "value", validated)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Registration deadlines
# ---------------------------------------------------------------------------


class DeadlineKind(StrEnum):
    """The independent registration deadlines a competition can enforce.

    Registration is not a single date: applications, payment, media uploads,
    document uploads and corrections each close on their own schedule. New deadline
    kinds are added here (the enum is the extension point).
    """

    APPLICATION = "APPLICATION"
    PAYMENT = "PAYMENT"
    MUSIC_UPLOAD = "MUSIC_UPLOAD"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    CORRECTION = "CORRECTION"


@dataclass(frozen=True, slots=True)
class RegistrationDeadlines:
    """The independent registration deadlines, each an optional cut-off instant.

    A ``None`` deadline means "no cut-off" for that activity. All instants are
    timezone-aware :class:`~datetime.datetime` so they compare directly to ``now``.

    Invariant (deadlines must not contradict): the *correction* deadline must not
    fall before the *application* deadline — corrections happen after applying.
    Further cross-deadline rules can be added here as the model matures.
    """

    application: datetime | None = None
    payment: datetime | None = None
    music_upload: datetime | None = None
    document_upload: datetime | None = None
    correction: datetime | None = None

    def __post_init__(self) -> None:
        if self.application is not None and self.correction is not None and self.correction < self.application:
            raise InvalidRegistrationDeadlinesError("The correction deadline must not precede the application deadline.")

    def _deadline(self, kind: DeadlineKind) -> datetime | None:
        return {
            DeadlineKind.APPLICATION: self.application,
            DeadlineKind.PAYMENT: self.payment,
            DeadlineKind.MUSIC_UPLOAD: self.music_upload,
            DeadlineKind.DOCUMENT_UPLOAD: self.document_upload,
            DeadlineKind.CORRECTION: self.correction,
        }[kind]

    def is_open(self, kind: DeadlineKind, now: datetime) -> bool:
        """Whether ``kind`` is still open at ``now`` (open when unset or not yet past)."""
        deadline = self._deadline(kind)
        return deadline is None or now <= deadline


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompetitionSettings:
    """Immutable bag of competition **behaviour** flags, kept off the aggregate root.

    Groups the policy toggles that govern how applications behave, so the root is
    not littered with booleans. Every flag defaults to a conservative value, which
    keeps this value object **extensible**: new flags are appended with a default,
    so existing construction sites and persisted rows keep working unchanged.

    Replace wholesale via :meth:`~apps.competitions.domain.entities.Competition.update_settings`;
    :meth:`with_changes` builds a modified copy conveniently.
    """

    allow_multiple_applications: bool = False
    allow_application_editing: bool = True
    allow_music_replacement: bool = True
    allow_video_replacement: bool = True
    allow_participant_changes: bool = True
    require_music_upload: bool = False
    require_video_upload: bool = False
    require_photo_upload: bool = False
    require_identity_document: bool = False
    require_parent_consent: bool = False
    require_teacher: bool = False
    require_comment_for_application: bool = False

    @classmethod
    def default(cls) -> CompetitionSettings:
        """The default settings a competition starts with."""
        return cls()

    def with_changes(self, **changes: bool) -> CompetitionSettings:
        """A copy with the given flags overridden (rejects unknown flag names)."""
        return replace(self, **changes)


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompetitionBranding:
    """The competition's visual identity as explicit, optional file references.

    Groups the branding assets (logo, banner, poster) into one value object rather
    than scattering them across the root. Each is a storage-agnostic
    :class:`FileReference`; resolving one to bytes is an infrastructure concern.
    """

    logo: FileReference | None = None
    banner: FileReference | None = None
    poster: FileReference | None = None

    @classmethod
    def empty(cls) -> CompetitionBranding:
        """Branding with no assets set."""
        return cls()
