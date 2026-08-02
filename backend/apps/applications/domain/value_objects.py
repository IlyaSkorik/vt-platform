"""Value objects for the Applications (Competition Submission) bounded context.

Immutable, identity-less concepts of the Submission domain. Each is a frozen,
slotted dataclass that validates on construction, compares by value, and can
never be mutated. **Pure domain code** (ARCH-001 §4.1, §7.2): standard library
only - no Django, no ORM, no third-party validators.

Value objects here fall into these groups:

* **Local identifiers** (UUID v7, one distinct type per aggregate/child):
  :class:`SubmissionId`, :class:`ParticipantId`, :class:`TeacherId`,
  :class:`AttachmentId`, :class:`ReviewId`.
* **Foreign references** (held by id only - no cross-context import edge):
  :class:`CompetitionId` (the competition applied to), :class:`UserId` (the
  applicant), :class:`ReviewerId` (the organizer reviewer), and the five
  Competition-configuration references a performance names - :class:`NominationId`,
  :class:`DisciplineId`, :class:`AgeCategoryId`, :class:`ParticipantGroupId`,
  :class:`ParticipationFormatId`. The Submission never resolves these; the
  Competition configuration arrives later through a read model / ACL.
* **Content VOs**: :class:`Performance` (the single competitive act), :class:`PersonName`,
  :class:`BirthDate`, :class:`Duration`, :class:`FileReference`, :class:`TeacherRole`,
  :class:`ReviewComment`.
* **Enumerations**: :class:`SubmissionStatus`, :class:`Gender`, :class:`AttachmentType`,
  :class:`Currency`.
* **Money & pricing**: :class:`Money`, :class:`PriceSnapshot` (the immutable price
  frozen at submission), :class:`ParticipantCountRange`, and
  :class:`SubmissionParticipationPolicy` (the projected slice of Competition rules a
  submission validates itself against).

The id value objects intentionally duplicate the UUID-v7 logic that also exists
in the Identity, Organization and Competition contexts: the bounded contexts stay
independent (no shared import edge), so a little duplication is preferred over a
cross-context dependency (ARCH-001 §14).
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from .exceptions import (
    InvalidAgeCategoryIdError,
    InvalidApplicationIdError,
    InvalidApplicationStatusChangeError,
    InvalidAttachmentIdError,
    InvalidBirthDateError,
    InvalidCompetitionIdError,
    InvalidConsentError,
    InvalidDirectoryTeacherIdError,
    InvalidDisciplineIdError,
    InvalidDurationError,
    InvalidEducationalOrganizationIdError,
    InvalidFileReferenceError,
    InvalidMoneyError,
    InvalidNominationIdError,
    InvalidOrganizationNameError,
    InvalidParticipantCountRangeError,
    InvalidParticipantGroupIdError,
    InvalidParticipantIdError,
    InvalidParticipationFormatIdError,
    InvalidPaymentReceiptError,
    InvalidPaymentReceiptIdError,
    InvalidPerformanceCommentError,
    InvalidPerformanceTitleError,
    InvalidPersonNameError,
    InvalidPriceSnapshotError,
    InvalidRegistryParticipantIdError,
    InvalidReviewCommentError,
    InvalidReviewerIdError,
    InvalidReviewIdError,
    InvalidServiceIdError,
    InvalidServiceLineError,
    InvalidSubmissionIdError,
    InvalidSubmissionRefError,
    InvalidSubmissionStatusChangeError,
    InvalidTeacherIdError,
    InvalidTeacherRoleError,
    InvalidTotalPriceSnapshotError,
    InvalidUserIdError,
)

__all__ = [
    "AgeCategoryId",
    "ApplicationId",
    "ApplicationStatus",
    "ApplicationStatusChange",
    "AttachmentId",
    "AttachmentType",
    "BirthDate",
    "CompetitionId",
    "CompetitionPriceQuote",
    "Consent",
    "Currency",
    "DirectoryTeacherId",
    "DisciplineId",
    "Duration",
    "EducationalOrganizationId",
    "FileReference",
    "Gender",
    "Money",
    "NominationId",
    "OrganizationName",
    "ParticipantCountRange",
    "ParticipantGroupId",
    "ParticipantId",
    "ParticipationFormatId",
    "PaymentReceipt",
    "PaymentReceiptId",
    "Performance",
    "PersonName",
    "PriceCalculationType",
    "PriceSnapshot",
    "RegistryParticipantId",
    "ReviewComment",
    "ReviewId",
    "ReviewerId",
    "ServiceId",
    "ServiceLine",
    "SubmissionId",
    "SubmissionParticipationPolicy",
    "SubmissionRef",
    "SubmissionStatus",
    "SubmissionStatusChange",
    "TeacherId",
    "TeacherRole",
    "TotalPriceSnapshot",
    "UserId",
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
# Local identifiers (UUID v7, one distinct type per aggregate/child)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class SubmissionId:
    """The globally unique identity of a :class:`Submission` aggregate (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidSubmissionIdError(f"SubmissionId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidSubmissionIdError(f"SubmissionId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> SubmissionId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> SubmissionId:
        """Build a ``SubmissionId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> SubmissionId:
        """Parse a canonical UUID string, or raise :class:`InvalidSubmissionIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidSubmissionIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"SubmissionId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ParticipantId:
    """The identity of a :class:`~apps.applications.domain.entities.Participant` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidParticipantIdError(f"ParticipantId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidParticipantIdError(f"ParticipantId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ParticipantId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ParticipantId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ParticipantId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidParticipantIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ParticipantId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class TeacherId:
    """The identity of a :class:`~apps.applications.domain.entities.Teacher` child entity (UUID v7)."""

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
class AttachmentId:
    """The identity of an :class:`~apps.applications.domain.entities.Attachment` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidAttachmentIdError(f"AttachmentId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidAttachmentIdError(f"AttachmentId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> AttachmentId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> AttachmentId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> AttachmentId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidAttachmentIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"AttachmentId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class PaymentReceiptId:
    """The identity of one :class:`PaymentReceipt` on an order (UUID v7).

    An order may carry several receipts (a fee settled by more than one transfer),
    so each needs its own handle: without one the applicant could only add to the
    pile, never point at the wrong file and take it back.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidPaymentReceiptIdError(f"PaymentReceiptId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidPaymentReceiptIdError(f"PaymentReceiptId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> PaymentReceiptId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> PaymentReceiptId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> PaymentReceiptId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidPaymentReceiptIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"PaymentReceiptId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ReviewId:
    """The identity of a :class:`~apps.applications.domain.entities.Review` child entity (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidReviewIdError(f"ReviewId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidReviewIdError(f"ReviewId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ReviewId:
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ReviewId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ReviewId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidReviewIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ReviewId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# Foreign references (opaque UUID v7 ids - no cross-context import edge)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class CompetitionId:
    """A reference to the competition applied to, held only as an opaque UUID v7.

    Deliberately a **separate** type from the Competitions context's own
    ``CompetitionId`` so the two contexts share no import edge (ARCH-001 §14). The
    Submission knows the competition solely by this id; its configuration arrives
    later through a read model / ACL.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidCompetitionIdError(f"CompetitionId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidCompetitionIdError(f"CompetitionId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> CompetitionId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> CompetitionId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCompetitionIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"CompetitionId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class UserId:
    """A reference to the applicant (the authenticated user who owns the submission).

    Held only as an opaque UUID v7 - a separate type from the Identity context's
    own user id so the two contexts share no import edge (ARCH-001 §14).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidUserIdError(f"UserId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidUserIdError(f"UserId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> UserId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> UserId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidUserIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"UserId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ReviewerId:
    """A reference to the organizer who authored a review, held only as an opaque UUID v7.

    A separate type from :class:`UserId` because a reviewer acts in an organizer
    capacity; keeping the roles distinct documents intent even though both resolve
    to a user in another context (never imported here).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidReviewerIdError(f"ReviewerId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidReviewerIdError(f"ReviewerId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ReviewerId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ReviewerId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidReviewerIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ReviewerId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class NominationId:
    """A reference to a Competition nomination/category, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidNominationIdError(f"NominationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidNominationIdError(f"NominationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> NominationId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> NominationId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidNominationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"NominationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class DisciplineId:
    """A reference to a Competition discipline, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidDisciplineIdError(f"DisciplineId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidDisciplineIdError(f"DisciplineId must be a UUID v7, got version {self.value.version}.")

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
    """A reference to a Competition age category, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidAgeCategoryIdError(f"AgeCategoryId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidAgeCategoryIdError(f"AgeCategoryId must be a UUID v7, got version {self.value.version}.")

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
    """A reference to a Competition participant group, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidParticipantGroupIdError(f"ParticipantGroupId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidParticipantGroupIdError(f"ParticipantGroupId must be a UUID v7, got version {self.value.version}.")

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
    """A reference to a Competition participation format, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidParticipationFormatIdError(f"ParticipationFormatId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidParticipationFormatIdError(f"ParticipationFormatId must be a UUID v7, got version {self.value.version}.")

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
class RegistryParticipantId:
    """A reference to the applicant's Participant Registry entry, held by id only (UUID v7).

    The submission's :class:`~apps.applications.domain.entities.Participant` links to
    a reusable registry participant (solo or collective) by this opaque id; the
    participant's name/birth-date/gender fields are a denormalized snapshot of that
    registry record. A separate type from the Participants context's own id so the
    two contexts share no import edge (ARCH-001 §14).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidRegistryParticipantIdError(f"RegistryParticipantId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidRegistryParticipantIdError(f"RegistryParticipantId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> RegistryParticipantId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> RegistryParticipantId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidRegistryParticipantIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"RegistryParticipantId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class DirectoryTeacherId:
    """A reference to the applicant's Teacher Directory entry, held by id only (UUID v7).

    A submission credits a teacher chosen from the reusable, user-owned Teacher
    Directory; the credited :class:`~apps.applications.domain.entities.Teacher`
    keeps this link plus a denormalized name/role snapshot. A separate type from the
    Teachers context's own id so the two contexts share no import edge (ARCH-001
    §14). Manual, directory-less credits leave this ``None``.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidDirectoryTeacherIdError(f"DirectoryTeacherId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidDirectoryTeacherIdError(f"DirectoryTeacherId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> DirectoryTeacherId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> DirectoryTeacherId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidDirectoryTeacherIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"DirectoryTeacherId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SubmissionStatus(StrEnum):
    """The submission's lifecycle state.

    ``DRAFT``               - the applicant is assembling the submission; content is mutable.
    ``SUBMITTED``           - submitted to the competition; awaiting organizer intake.
    ``UNDER_REVIEW``        - the organizer is reviewing it.
    ``REQUIRES_CORRECTION`` - returned to the applicant to fix; content is mutable again.
    ``APPROVED``            - the organizer approved it.
    ``WAITING_PAYMENT``     - approved and awaiting payment.
    ``PAID``                - payment settled.
    ``ACCEPTED``            - accepted into the competition; content is frozen permanently.
    ``SCHEDULED``           - assigned a slot in the running order.
    ``COMPLETED``           - the performance took place.
    ``CANCELLED``           - withdrawn or rejected; terminal.

    From ``ACCEPTED`` on, the applicant can no longer withdraw; the organizer may
    still cancel, case by case, until the performance has taken place.

    Legal transitions are enforced by the :class:`~apps.applications.domain.entities.
    Submission` aggregate; this enum only names the states.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
    APPROVED = "APPROVED"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    ACCEPTED = "ACCEPTED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class SubmissionStatusChange:
    """One entry in a submission's status history - a past transition, timestamped."""

    from_status: SubmissionStatus | None
    to_status: SubmissionStatus
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.from_status is not None and not isinstance(self.from_status, SubmissionStatus):
            raise InvalidSubmissionStatusChangeError(
                f"from_status must be a SubmissionStatus or None, got {type(self.from_status)!r}."
            )
        if not isinstance(self.to_status, SubmissionStatus):
            raise InvalidSubmissionStatusChangeError(
                f"to_status must be a SubmissionStatus, got {type(self.to_status)!r}."
            )
        if not isinstance(self.occurred_at, datetime):
            raise InvalidSubmissionStatusChangeError(
                f"occurred_at must be a datetime, got {type(self.occurred_at)!r}."
            )


class Gender(StrEnum):
    """A participant's gender.

    ``OTHER`` accommodates participants whose Participant Registry record uses a
    non-binary value; it also lets a collective (which has no single gender) be
    represented without a gender at all (the field is optional on the participant).
    """

    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class AttachmentType(StrEnum):
    """The kind of file an attachment references.

    A fixed vocabulary of the media a submission carries today; new kinds are added
    here (the enum is the extension point). The domain stores only a
    :class:`FileReference` per attachment - never the bytes.

    ``BENEFIT`` is deliberately distinct from ``DOCUMENT``. A ``DOCUMENT`` is the
    supporting paperwork a competition may *require* of everyone
    (``require_document_upload``); a ``BENEFIT`` is the certificate an applicant
    *chooses* to attach to claim a reduced fee. Conflating the two would let a
    competition's mandatory document read as a benefit claim.
    """

    MUSIC = "MUSIC"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    BENEFIT = "BENEFIT"


class Currency(StrEnum):
    """An ISO-4217 currency code a price is denominated in (default ``BYN``)."""

    BYN = "BYN"


# ---------------------------------------------------------------------------
# Content value objects
# ---------------------------------------------------------------------------

_PERFORMANCE_TITLE_MAX: Final = 300
_PERFORMANCE_COMMENT_MAX: Final = 1_000
_FIRST_NAME_MAX: Final = 120
_LAST_NAME_MAX: Final = 120
_MIDDLE_NAME_MAX: Final = 120
_TEACHER_ROLE_MAX: Final = 120
_FILE_REFERENCE_MAX: Final = 1_024
_REVIEW_COMMENT_MAX: Final = 5_000
_DURATION_MAX_SECONDS: Final = 24 * 60 * 60  # a day is a generous, sanity upper bound
_EARLIEST_BIRTH_YEAR: Final = 1900


@dataclass(frozen=True, slots=True)
class PerformanceTitle:
    """A non-empty, length-bounded performance title."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidPerformanceTitleError("Performance title must not be empty.")
        if len(stripped) > _PERFORMANCE_TITLE_MAX:
            raise InvalidPerformanceTitleError(f"Performance title must be at most {_PERFORMANCE_TITLE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Duration:
    """A performance duration, stored as a whole number of seconds.

    Stored as an :class:`int` (not a float) to avoid rounding error; exposed as a
    :class:`~datetime.timedelta` for convenience. Must be strictly positive and not
    implausibly long (a day is the sanity ceiling).
    """

    seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
            raise InvalidDurationError(f"Duration seconds must be an int, got {type(self.seconds)!r}.")
        if self.seconds <= 0:
            raise InvalidDurationError(f"Duration must be positive, got {self.seconds} seconds.")
        if self.seconds > _DURATION_MAX_SECONDS:
            raise InvalidDurationError(f"Duration must be at most {_DURATION_MAX_SECONDS} seconds.")

    @classmethod
    def of_seconds(cls, seconds: int) -> Duration:
        """Build a :class:`Duration` from a whole number of seconds."""
        return cls(seconds=seconds)

    @classmethod
    def of(cls, *, minutes: int = 0, seconds: int = 0) -> Duration:
        """Build a :class:`Duration` from minutes and/or seconds."""
        return cls(seconds=minutes * 60 + seconds)

    @property
    def as_timedelta(self) -> timedelta:
        """The duration as a :class:`~datetime.timedelta`."""
        return timedelta(seconds=self.seconds)

    def __str__(self) -> str:
        minutes, seconds = divmod(self.seconds, 60)
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class PersonName:
    """A person's name - last and first are required, middle (patronymic) optional.

    Used for both participants and teachers. The three components are stored
    separately (rather than a single string) so the domain can compare and present
    them structurally; the value object trims and bounds each part.
    """

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
class BirthDate:
    """A participant's date of birth (a calendar date, no time-of-day).

    The value object enforces a sane lower bound; the "not in the future" check
    needs the current instant and so is enforced by the aggregate when a
    participant is added (``now`` is injected there, never read here).
    """

    value: date

    def __post_init__(self) -> None:
        if not isinstance(self.value, date) or isinstance(self.value, datetime):
            raise InvalidBirthDateError("BirthDate must be a datetime.date (not a datetime).")
        if self.value.year < _EARLIEST_BIRTH_YEAR:
            raise InvalidBirthDateError(f"BirthDate year must be {_EARLIEST_BIRTH_YEAR} or later, got {self.value.year}.")

    def age_at(self, reference: date) -> int:
        """The age in whole years at ``reference`` (birthday-aware)."""
        years = reference.year - self.value.year
        if (reference.month, reference.day) < (self.value.month, self.value.day):
            years -= 1
        return years

    def __str__(self) -> str:
        return self.value.isoformat()


@dataclass(frozen=True, slots=True)
class TeacherRole:
    """A configurable teacher role label (e.g. Teacher, Concertmaster, Choreographer).

    Deliberately a free-form, length-bounded string rather than a fixed enum: the
    set of roles is **configurable** per the platform's needs (Director, Producer,
    Accompanist, ...), so the domain stores an opaque, non-empty label and leaves
    the vocabulary to configuration.
    """

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
class FileReference:
    """An opaque reference to a stored file (a storage key or URL).

    The domain treats it as an opaque, length-bounded token: it neither knows nor
    cares whether it is an S3 key, a CDN URL, or a local path - resolving it to
    bytes is an infrastructure concern. Used for every attachment.
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
class ReviewComment:
    """A non-empty, length-bounded organizer review comment."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidReviewCommentError("Review comment must not be empty.")
        if len(stripped) > _REVIEW_COMMENT_MAX:
            raise InvalidReviewCommentError(f"Review comment must be at most {_REVIEW_COMMENT_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Performance:
    """The single competitive act a submission is built around.

    Exactly one per submission. It carries its own descriptive data (title,
    duration) and **references** the Competition configuration it competes under by
    id only - a nomination, discipline, age category, participant group and
    participation format. The Submission never duplicates or resolves that
    configuration; a read model / ACL validates the references when the submission
    is submitted.

    Modelled as a value object (not a child entity) because there is exactly one
    per submission and no independent identity: editing the performance replaces
    the whole value.

    ``comment`` is the applicant's optional free-text note for the organizers about
    this act (stage entry point, props, equipment, backing-track quirks). It is
    plain, length-bounded text - an empty string means "nothing to add" (the same
    "blank, not null" shape :class:`Attachment`'s caption uses).
    """

    title: PerformanceTitle
    duration: Duration
    nomination_id: NominationId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId
    comment: str = ""

    def __post_init__(self) -> None:
        stripped = self.comment.strip()
        if len(stripped) > _PERFORMANCE_COMMENT_MAX:
            raise InvalidPerformanceCommentError(f"Performance comment must be at most {_PERFORMANCE_COMMENT_MAX} characters.")
        object.__setattr__(self, "comment", stripped)

    def __str__(self) -> str:
        return f"{self.title} ({self.duration})"


# ---------------------------------------------------------------------------
# Money & pricing
# ---------------------------------------------------------------------------

_MONEY_QUANTUM: Final = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """A non-negative monetary amount in a single currency, quantized to 2 dp.

    Amounts are stored as :class:`~decimal.Decimal` to avoid binary-float rounding
    error. Duplicated (rather than shared) with the Competitions context so the two
    stay independent (ARCH-001 §14).
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
        except InvalidOperation as exc:
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


class PriceCalculationType(StrEnum):
    """How a competition unit price becomes a submission total (ACL projection)."""

    PER_PARTICIPANT = "PER_PARTICIPANT"
    PER_PERFORMANCE = "PER_PERFORMANCE"


@dataclass(frozen=True, slots=True)
class CompetitionPriceQuote:
    """Competition list price for one combination, projected into this context."""

    unit_price: Money
    calculation_type: PriceCalculationType = PriceCalculationType.PER_PARTICIPANT

    def total_for(self, participant_count: int) -> Money:
        if participant_count < 1:
            raise InvalidMoneyError("Participant count must be at least 1 to compute a total.")
        if self.calculation_type is PriceCalculationType.PER_PERFORMANCE:
            return self.unit_price
        return Money.of(self.unit_price.amount * participant_count, self.unit_price.currency)


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """The immutable price of a submission, frozen at the moment it was calculated.

    The Competition determines pricing; the Submission stores only this snapshot.
    Once a submission is submitted the snapshot **never changes** - future
    Competition pricing updates must not affect existing submissions. As a value
    object it cannot be mutated at all; the aggregate additionally forbids
    *replacing* it once the submission leaves the editable states.
    """

    price: Money
    calculated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.price, Money):
            raise InvalidPriceSnapshotError(f"PriceSnapshot price must be Money, got {type(self.price)!r}.")
        if not isinstance(self.calculated_at, datetime):
            raise InvalidPriceSnapshotError(f"PriceSnapshot calculated_at must be a datetime, got {type(self.calculated_at)!r}.")

    @property
    def amount(self) -> Decimal:
        """The snapshotted amount."""
        return self.price.amount

    @property
    def currency(self) -> Currency:
        """The snapshotted currency."""
        return self.price.currency

    def __str__(self) -> str:
        return f"{self.price} @ {self.calculated_at.isoformat()}"


@dataclass(frozen=True, slots=True)
class PaymentReceipt:
    """One piece of the applicant's proof of payment for the whole order.

    Unlike a submission attachment (which belongs to one performance), a receipt is
    an **order-level** artifact: it settles the application total, not a single
    number in it. An order keeps a *list* of them, because the total is regularly
    paid in more than one transfer — a school pays for part of a group and a parent
    for the rest, or the fee goes out in instalments — and each transfer produces
    its own slip. It pairs the stored file reference with the instant it was
    uploaded, under an id the applicant can use to take the wrong file back.
    """

    id: PaymentReceiptId
    file: FileReference
    uploaded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, PaymentReceiptId):
            raise InvalidPaymentReceiptError(f"PaymentReceipt id must be a PaymentReceiptId, got {type(self.id)!r}.")
        if not isinstance(self.file, FileReference):
            raise InvalidPaymentReceiptError(f"PaymentReceipt file must be a FileReference, got {type(self.file)!r}.")
        if not isinstance(self.uploaded_at, datetime):
            raise InvalidPaymentReceiptError(f"PaymentReceipt uploaded_at must be a datetime, got {type(self.uploaded_at)!r}.")

    def __str__(self) -> str:
        return f"{self.file} @ {self.uploaded_at.isoformat()}"


@dataclass(frozen=True, slots=True)
class ParticipantCountRange:
    """A participant-count band (e.g. Solo=1, Duet=2, Ensemble=3-5, Choir=6+).

    ``max_count`` is ``None`` for an open-ended upper bound (the ``6+`` case). A
    local copy of the Competition concept (never imported) used to validate that a
    submission's participant count matches its chosen participant group.
    """

    min_count: int
    max_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.min_count, int) or isinstance(self.min_count, bool):
            raise InvalidParticipantCountRangeError("Minimum count must be an integer.")
        if self.min_count < 1:
            raise InvalidParticipantCountRangeError(f"Minimum count must be at least 1, got {self.min_count}.")
        if self.max_count is not None:
            if not isinstance(self.max_count, int) or isinstance(self.max_count, bool):
                raise InvalidParticipantCountRangeError("Maximum count must be an integer or None.")
            if self.max_count < self.min_count:
                raise InvalidParticipantCountRangeError(f"Maximum count {self.max_count} must not be less than minimum {self.min_count}.")

    @property
    def is_open_ended(self) -> bool:
        """Whether the band has no upper bound."""
        return self.max_count is None

    def contains(self, count: int) -> bool:
        """Whether ``count`` falls within the band."""
        if count < self.min_count:
            return False
        return self.max_count is None or count <= self.max_count

    def __str__(self) -> str:
        return f"{self.min_count}+" if self.max_count is None else f"{self.min_count}-{self.max_count}"


@dataclass(frozen=True, slots=True)
class SubmissionParticipationPolicy:
    """The projected slice of Competition rules a submission validates itself against.

    An **anti-corruption read model**: the local, Submission-owned representation of
    just enough Competition configuration to enforce the participation invariants -
    whether the chosen combination is admissible, and the participant-count band of
    the chosen participant group. It is supplied to :meth:`Submission.submit` by the
    caller (the future application layer fetches it through an ACL); the domain
    never imports or resolves the Competition aggregate itself.
    """

    participant_count_range: ParticipantCountRange
    is_admissible: bool = True
    #: Competition requirements for the chosen participation format, projected so the
    #: submission can enforce them at submit without importing the Competition.
    requires_teacher: bool = False
    requires_music: bool = False
    requires_video_file: bool = False
    requires_document: bool = False
    #: Whether the competition invites the applicant's free-text note about the act.
    #: When a competition does not, a note that slipped in anyway (an older draft, a
    #: client that still renders the field) is rejected rather than quietly carried
    #: to organizers who never asked to read it.
    allows_participant_comment: bool = True

    def required_attachment_types(self) -> frozenset[AttachmentType]:
        """The attachment kinds this competition requires before submission.

        Music maps to :attr:`AttachmentType.MUSIC`, a file-mode video to
        :attr:`AttachmentType.VIDEO`, and a required supporting document to
        :attr:`AttachmentType.DOCUMENT`. The **payment receipt is deliberately not
        here**: it proves payment of the order and is attached to the Application
        after submission (see :class:`PaymentReceipt`), never as a submission
        attachment at submit time.
        """
        required: set[AttachmentType] = set()
        if self.requires_music:
            required.add(AttachmentType.MUSIC)
        if self.requires_video_file:
            required.add(AttachmentType.VIDEO)
        if self.requires_document:
            required.add(AttachmentType.DOCUMENT)
        return frozenset(required)

    def allows_participant_count(self, count: int) -> bool:
        """Whether ``count`` matches the configured participant group's band."""
        return self.participant_count_range.contains(count)


# ===========================================================================
# Application aggregate (order-level) value objects
# ===========================================================================
#
# Value objects for the sibling :class:`~apps.applications.domain.entities.
# Application` aggregate - the *order* that groups one applicant's Submissions
# for one competition. The Application references its Submissions by id and caches
# a display snapshot of each (:class:`SubmissionRef`); it owns the educational
# organization reference, the selected additional services, the recorded consents,
# and the immutable total price. Shared value objects (:class:`Money`,
# :class:`Currency`, :class:`SubmissionId`, :class:`CompetitionId`,
# :class:`UserId`, :class:`PriceSnapshot`) are reused, never duplicated.

_ORGANIZATION_NAME_MAX: Final = 300
_CONSENT_CODE_MAX: Final = 120
_CONSENT_VERSION_MAX: Final = 40
_SERVICE_NAME_MAX: Final = 300
_SUBMISSION_REF_LABEL_MAX: Final = 300
_SERVICE_QUANTITY_MAX: Final = 1_000


@dataclass(frozen=True, slots=True, repr=False)
class ApplicationId:
    """The globally unique identity of an :class:`Application` aggregate (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidApplicationIdError(f"ApplicationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidApplicationIdError(f"ApplicationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> ApplicationId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> ApplicationId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> ApplicationId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidApplicationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ApplicationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class EducationalOrganizationId:
    """A reference to the applicant's educational organization, held by id only (UUID v7).

    A separate type from any Institutions-context id so the two contexts share no
    import edge (ARCH-001 §14). The Application resolves the organization's display
    name through an ACL and freezes it as a snapshot; it never imports the aggregate.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidEducationalOrganizationIdError(f"EducationalOrganizationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidEducationalOrganizationIdError(f"EducationalOrganizationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> EducationalOrganizationId:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> EducationalOrganizationId:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidEducationalOrganizationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"EducationalOrganizationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class ServiceId:
    """A reference to a Competition additional service, held by id only (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidServiceIdError(f"ServiceId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidServiceIdError(f"ServiceId must be a UUID v7, got version {self.value.version}.")

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


class ApplicationStatus(StrEnum):
    """The application's (order) lifecycle state.

    ``DRAFT``           - the applicant is assembling the order; composition is mutable.
    ``SUBMITTED``       - the order was placed; its Submissions are under per-performance review.
    ``WAITING_PAYMENT`` - all referenced submissions are approved; the order awaits payment.
    ``PAID``            - the order's total was paid.
    ``COMPLETED``       - the order is fully settled.
    ``CANCELLED``       - the order was withdrawn or rejected; terminal.

    The Application deliberately carries **no** review states of its own: approval
    lives on the individual Submissions, and the order derives its readiness for
    payment from their statuses. Legal transitions are enforced by the
    :class:`~apps.applications.domain.entities.Application` aggregate.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class OrganizationName:
    """A frozen snapshot of an educational organization's display name.

    Stored on the Application at selection time so listing an application never has
    to resolve the Institutions context; the reference id is kept alongside for
    navigation.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidOrganizationNameError("Organization name must not be empty.")
        if len(stripped) > _ORGANIZATION_NAME_MAX:
            raise InvalidOrganizationNameError(f"Organization name must be at most {_ORGANIZATION_NAME_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Consent:
    """A single consent the applicant accepted, captured as an immutable snapshot.

    The ``code`` identifies the consent (e.g. ``personal_data``, ``media_release``)
    and ``version`` records which revision of the consent text was accepted, so the
    application preserves *what* was agreed even if the wording later changes.
    """

    code: str
    version: str
    accepted_at: datetime

    def __post_init__(self) -> None:
        code = self.code.strip()
        version = self.version.strip()
        if not code:
            raise InvalidConsentError("Consent code must not be empty.")
        if len(code) > _CONSENT_CODE_MAX:
            raise InvalidConsentError(f"Consent code must be at most {_CONSENT_CODE_MAX} characters.")
        if not version:
            raise InvalidConsentError("Consent version must not be empty.")
        if len(version) > _CONSENT_VERSION_MAX:
            raise InvalidConsentError(f"Consent version must be at most {_CONSENT_VERSION_MAX} characters.")
        if not isinstance(self.accepted_at, datetime):
            raise InvalidConsentError(f"Consent accepted_at must be a datetime, got {type(self.accepted_at)!r}.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "version", version)

    def __str__(self) -> str:
        return f"{self.code}@{self.version}"


@dataclass(frozen=True, slots=True)
class ServiceLine:
    """A selected additional service on the application: what, how many, at what price.

    Prices originate from the Competition (via an ACL) and are snapshotted here at
    selection time; ``name`` is a display snapshot so listing the order needs no
    Competition lookup. The line total is ``unit_price x quantity`` in the unit
    price's currency.
    """

    service_id: ServiceId
    name: str
    unit_price: Money
    quantity: int
    billing_model: PriceCalculationType = PriceCalculationType.PER_PARTICIPANT

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise InvalidServiceLineError("Service name must not be empty.")
        if not isinstance(self.billing_model, PriceCalculationType):
            raise InvalidServiceLineError(f"Service billing model must be a PriceCalculationType, got {type(self.billing_model)!r}.")
        if len(name) > _SERVICE_NAME_MAX:
            raise InvalidServiceLineError(f"Service name must be at most {_SERVICE_NAME_MAX} characters.")
        if not isinstance(self.unit_price, Money):
            raise InvalidServiceLineError(f"Service unit price must be Money, got {type(self.unit_price)!r}.")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise InvalidServiceLineError(f"Service quantity must be an int, got {type(self.quantity)!r}.")
        if self.quantity < 1:
            raise InvalidServiceLineError(f"Service quantity must be at least 1, got {self.quantity}.")
        if self.quantity > _SERVICE_QUANTITY_MAX:
            raise InvalidServiceLineError(f"Service quantity must be at most {_SERVICE_QUANTITY_MAX}.")
        object.__setattr__(self, "name", name)

    @property
    def line_total(self) -> Money:
        """The line's total cost - ``unit_price x quantity``."""
        return Money.of(self.unit_price.amount * self.quantity, self.unit_price.currency)

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity} ({self.line_total})"


@dataclass(frozen=True, slots=True)
class SubmissionRef:
    """A reference to a Submission plus the display snapshot the order UI needs.

    The Application never loads its Submissions to render a summary: it caches here
    exactly what the "my applications" screens show - the performance title, the
    lead participant's display name, the nomination and discipline labels, the
    frozen per-performance :class:`PriceSnapshot` (``None`` until the submission is
    priced), and the submission's current :class:`SubmissionStatus`. The status and
    price are kept fresh by an application-layer projection reacting to Submission
    events; the Application derives its readiness for payment from these statuses.
    """

    submission_id: SubmissionId
    performance_title: str
    participant_display_name: str
    nomination: str
    discipline: str
    status: SubmissionStatus
    price: PriceSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.submission_id, SubmissionId):
            raise InvalidSubmissionRefError(f"SubmissionRef submission_id must be a SubmissionId, got {type(self.submission_id)!r}.")
        if not isinstance(self.status, SubmissionStatus):
            raise InvalidSubmissionRefError(f"SubmissionRef status must be a SubmissionStatus, got {type(self.status)!r}.")
        if self.price is not None and not isinstance(self.price, PriceSnapshot):
            raise InvalidSubmissionRefError(f"SubmissionRef price must be a PriceSnapshot or None, got {type(self.price)!r}.")
        for label_name in ("performance_title", "participant_display_name", "nomination", "discipline"):
            raw = getattr(self, label_name)
            if not isinstance(raw, str):
                raise InvalidSubmissionRefError(f"SubmissionRef {label_name} must be a str, got {type(raw)!r}.")
            trimmed = raw.strip()
            if len(trimmed) > _SUBMISSION_REF_LABEL_MAX:
                raise InvalidSubmissionRefError(f"SubmissionRef {label_name} must be at most {_SUBMISSION_REF_LABEL_MAX} characters.")
            object.__setattr__(self, label_name, trimmed)

    @property
    def is_approved(self) -> bool:
        """Whether the referenced submission is approved (the payment-readiness signal)."""
        return self.status is SubmissionStatus.APPROVED

    @property
    def price_line(self) -> Money:
        """The submission's contribution to the order total (zero until it is priced)."""
        return self.price.price if self.price is not None else Money.of("0.00")

    def __str__(self) -> str:
        return f"{self.performance_title or self.submission_id.json()} [{self.status.value}]"


@dataclass(frozen=True, slots=True)
class TotalPriceSnapshot:
    """The immutable total price of an application, frozen when it leaves ``DRAFT``.

    ``total`` is ``submissions_total + services_total``. As a value object it cannot
    be mutated; the aggregate additionally forbids *recomputing* it once the
    application is submitted, so later Competition pricing changes can never alter
    the price of an order already placed.
    """

    total: Money
    submissions_total: Money
    services_total: Money
    calculated_at: datetime

    def __post_init__(self) -> None:
        for money_name in ("total", "submissions_total", "services_total"):
            money = getattr(self, money_name)
            if not isinstance(money, Money):
                raise InvalidTotalPriceSnapshotError(f"TotalPriceSnapshot {money_name} must be Money, got {type(money)!r}.")
        if not isinstance(self.calculated_at, datetime):
            raise InvalidTotalPriceSnapshotError(f"TotalPriceSnapshot calculated_at must be a datetime, got {type(self.calculated_at)!r}.")
        if not (self.total.currency == self.submissions_total.currency == self.services_total.currency):
            raise InvalidTotalPriceSnapshotError("TotalPriceSnapshot components must share one currency.")

    @property
    def amount(self) -> Decimal:
        return self.total.amount

    @property
    def currency(self) -> Currency:
        return self.total.currency

    def __str__(self) -> str:
        return f"{self.total} @ {self.calculated_at.isoformat()}"


@dataclass(frozen=True, slots=True)
class ApplicationStatusChange:
    """One entry in an application's status history - a past transition, timestamped.

    Recorded append-only by the aggregate on every lifecycle transition (including
    the initial ``None -> DRAFT``), so the whole order history can be shown without
    a separate audit store.
    """

    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.from_status is not None and not isinstance(self.from_status, ApplicationStatus):
            raise InvalidApplicationStatusChangeError(f"from_status must be an ApplicationStatus or None, got {type(self.from_status)!r}.")
        if not isinstance(self.to_status, ApplicationStatus):
            raise InvalidApplicationStatusChangeError(f"to_status must be an ApplicationStatus, got {type(self.to_status)!r}.")
        if not isinstance(self.occurred_at, datetime):
            raise InvalidApplicationStatusChangeError(f"occurred_at must be a datetime, got {type(self.occurred_at)!r}.")

    def __str__(self) -> str:
        origin = self.from_status.value if self.from_status is not None else "(none)"
        return f"{origin} -> {self.to_status.value}"
