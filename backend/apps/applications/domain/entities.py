"""Domain entities for the Applications (Competition Submission) bounded context.

One aggregate - the :class:`Submission` - representing **one competitive
performance submitted to one competition**. It owns only the information required
to participate: the single performance, the participants, the teachers, the
attachment references, the organizer review history, the immutable price
snapshot, and the lifecycle status. It does **not** own competition
configuration, pricing rules, scheduling, judging, results, diplomas or payments -
those live in their own contexts and are referenced by id only.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only - no Django, no
ORM, no clock, no IO. Time is always supplied by the caller (``now``).

Design contract (mirrors the Identity ``User`` and Competition aggregates):

* **No direct construction of the root.** Build a :class:`Submission` only via
  :meth:`Submission.draft` or :meth:`Submission.rehydrate` (reconstruction from
  persistence, which re-validates nothing and emits nothing).
* **Encapsulated state.** All fields private; only read-only views exposed. Child
  entities and content are mutated **only** through root methods, so every
  invariant is enforced in one place.
* **Root behaviour returns events, never publishes them.** Methods validate
  invariants, mutate state, bump ``updated_at``/``version``, and return the domain
  events they produced. Dispatch is an outer-layer concern.
* **Invalid transitions raise** typed errors - never silently ignored.

**Aggregate boundary.** :class:`Participant`, :class:`Teacher`, :class:`Attachment`
and :class:`Review` are **child entities** of the Submission (local identity, no
independent version - the root carries the aggregate's optimistic-concurrency
version). The single :class:`~apps.applications.domain.value_objects.Performance`
and the :class:`~apps.applications.domain.value_objects.PriceSnapshot` are value
objects. Everything loads and saves as one unit because the submission's
invariants are local to it (participant count, duplicate detection, "a submission
must have a performance, at least one participant and a frozen price before it may
be submitted"). The Submission is the correct, cohesive boundary: it is precisely
the set of data that must stay mutually consistent for one performance to compete.

**Why the Competition is *not* inside this boundary.** Admissibility and
participant-group rules belong to the Competition; the Submission validates
against a *projection* of them (a
:class:`~apps.applications.domain.value_objects.SubmissionParticipationPolicy` read
model passed into :meth:`submit`), never by importing the Competition aggregate.
This keeps the two aggregates independently consistent and the contexts decoupled.

**Future extension points (documented, deliberately NOT implemented).** The model
is shaped so these land as *additions*, not rewrites:

* *Promo codes / discounts / payment plans* - a checkout-stage concern computed
  *from* the frozen :class:`PriceSnapshot`, never mutating it.
* *Online performance links* - a new
  :class:`~apps.applications.domain.value_objects.AttachmentType` member or a
  dedicated value object on the performance.
* *Accommodation / transport requests* - separate contexts referencing the
  submission by id; here only the reference would live.
* *Custom participant fields / medical information / special requirements* - new
  optional value objects on :class:`Participant` (see its documented extension
  points: citizenship, identity document, disability, achievements).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Final

from .events import (
    AdditionalServiceRemoved,
    AdditionalServiceSelected,
    ApplicationAwaitingPayment,
    ApplicationCancelled,
    ApplicationCompleted,
    ApplicationCreated,
    ApplicationPaid,
    ApplicationSubmitted,
    AttachmentAdded,
    AttachmentRemoved,
    ConsentsRecorded,
    DomainEvent,
    EducationalOrganizationSelected,
    ParticipantAdded,
    ParticipantRemoved,
    PaymentReceiptUploaded,
    PerformanceDefined,
    PriceSnapshotCreated,
    ReviewAdded,
    SubmissionAccepted,
    SubmissionApproved,
    SubmissionAttachedToApplication,
    SubmissionAwaitingPayment,
    SubmissionCancelled,
    SubmissionCompleted,
    SubmissionCreated,
    SubmissionDetachedFromApplication,
    SubmissionPaid,
    SubmissionReturnedForCorrection,
    SubmissionReviewStarted,
    SubmissionScheduled,
    SubmissionSubmitted,
    TeacherAdded,
    TeacherRemoved,
)
from .exceptions import (
    ApplicationNotEditableError,
    AttachmentNotFoundError,
    CombinationNotAdmissibleError,
    DirectApplicationConstructionError,
    DirectConstructionError,
    DuplicateAttachmentError,
    DuplicateParticipantError,
    DuplicateServiceLineError,
    DuplicateSubmissionRefError,
    IllegalApplicationStatusTransitionError,
    IllegalStatusTransitionError,
    InvalidBirthDateError,
    InvalidParticipantMemberCountError,
    InvalidPersonNameError,
    MissingRequiredConsentError,
    MissingRequiredServiceError,
    NoSubmissionsError,
    NotAllSubmissionsApprovedError,
    ParticipantCountMismatchError,
    ParticipantNotFoundError,
    ParticipantRequiredError,
    PaymentReceiptNotAllowedError,
    PerformanceRequiredError,
    PriceSnapshotLockedError,
    PriceSnapshotRequiredError,
    RequiredAttachmentMissingError,
    ServiceLineNotFoundError,
    SubmissionNotEditableError,
    SubmissionRefNotFoundError,
    TeacherNotFoundError,
    TeacherRequiredError,
    TotalPriceLockedError,
)
from .value_objects import (
    ApplicationId,
    ApplicationStatus,
    ApplicationStatusChange,
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    Consent,
    Currency,
    DirectoryTeacherId,
    EducationalOrganizationId,
    FileReference,
    Gender,
    Money,
    OrganizationName,
    ParticipantId,
    PaymentReceipt,
    Performance,
    PersonName,
    PriceSnapshot,
    RegistryParticipantId,
    ReviewComment,
    ReviewerId,
    ReviewId,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionParticipationPolicy,
    SubmissionRef,
    SubmissionStatus,
    TeacherId,
    TeacherRole,
    TotalPriceSnapshot,
    UserId,
)

_CREATION_TOKEN: Final = object()

#: The lifecycle transitions the aggregate permits. ``COMPLETED`` and ``CANCELLED``
#: are terminal. Cancellation is possible until a submission is ``ACCEPTED``; from
#: ``ACCEPTED`` onward the submission is committed to the running order.
_LEGAL_TRANSITIONS: Final[dict[SubmissionStatus, frozenset[SubmissionStatus]]] = {
    SubmissionStatus.DRAFT: frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.SUBMITTED: frozenset({SubmissionStatus.UNDER_REVIEW, SubmissionStatus.CANCELLED}),
    SubmissionStatus.UNDER_REVIEW: frozenset({SubmissionStatus.APPROVED, SubmissionStatus.REQUIRES_CORRECTION, SubmissionStatus.CANCELLED}),
    SubmissionStatus.REQUIRES_CORRECTION: frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.APPROVED: frozenset({SubmissionStatus.WAITING_PAYMENT, SubmissionStatus.CANCELLED}),
    SubmissionStatus.WAITING_PAYMENT: frozenset({SubmissionStatus.PAID, SubmissionStatus.CANCELLED}),
    SubmissionStatus.PAID: frozenset({SubmissionStatus.ACCEPTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.ACCEPTED: frozenset({SubmissionStatus.SCHEDULED}),
    SubmissionStatus.SCHEDULED: frozenset({SubmissionStatus.COMPLETED}),
    SubmissionStatus.COMPLETED: frozenset(),
    SubmissionStatus.CANCELLED: frozenset(),
}

#: Statuses in which the submission's content (performance, participants, teachers,
#: attachments, price snapshot) may still be edited. Beyond these it is frozen.
_EDITABLE_STATUSES: Final = frozenset({SubmissionStatus.DRAFT, SubmissionStatus.REQUIRES_CORRECTION})

#: Statuses in which the organizer may record a review iteration.
_REVIEWABLE_STATUSES: Final = frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW})


# ===========================================================================
# Child entities
# ===========================================================================
#
# Child entities have local identity and value-by-id equality but carry **no**
# optimistic-concurrency version and emit no events - the root owns the aggregate's
# version and its event stream. They are created and mutated only by the
# :class:`Submission` root (their ``create``/``rehydrate`` classmethods are
# aggregate-internal by convention), which is why they need no direct-construction
# token of their own.


@dataclass(slots=True, eq=False, repr=False)
class Participant:
    """A participant on the performance - a snapshot of a Participant Registry entry.

    A participant is normally selected from the applicant's reusable Participant
    Registry, so it links back to that record by :class:`RegistryParticipantId` and
    carries a denormalized snapshot for display and records. It represents either a
    **solo** person (structured ``name`` + ``birth_date`` + ``gender``) or a
    **collective/ensemble** (only a ``display_name``, no birth date or gender). The
    ``display_name`` is always present; the structured fields are optional so a
    collective - and a registry gender the flat model does not carry - fit cleanly.

    Manual, registry-less entry is still supported (``registry_participant_id`` is
    ``None``) for backward compatibility.
    """

    _id: ParticipantId
    _display_name: str
    _name: PersonName | None = None
    _birth_date: BirthDate | None = None
    _gender: Gender | None = None
    _registry_participant_id: RegistryParticipantId | None = None
    _member_count: int = 1

    @classmethod
    def create(
        cls,
        *,
        participant_id: ParticipantId,
        name: PersonName | None = None,
        birth_date: BirthDate | None = None,
        gender: Gender | None = None,
        display_name: str | None = None,
        registry_participant_id: RegistryParticipantId | None = None,
        member_count: int = 1,
    ) -> Participant:
        resolved = cls._resolve_display_name(display_name, name)
        return cls(
            _id=participant_id,
            _display_name=resolved,
            _name=name,
            _birth_date=birth_date,
            _gender=gender,
            _registry_participant_id=registry_participant_id,
            _member_count=cls._validate_member_count(member_count),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        participant_id: ParticipantId,
        display_name: str | None = None,
        name: PersonName | None = None,
        birth_date: BirthDate | None = None,
        gender: Gender | None = None,
        registry_participant_id: RegistryParticipantId | None = None,
        member_count: int = 1,
    ) -> Participant:
        return cls(
            _id=participant_id,
            _display_name=cls._resolve_display_name(display_name, name),
            _name=name,
            _birth_date=birth_date,
            _gender=gender,
            _registry_participant_id=registry_participant_id,
            _member_count=cls._validate_member_count(member_count),
        )

    @staticmethod
    def _validate_member_count(member_count: int) -> int:
        """A solo entry counts as one; a collective carries its headcount (>= 1)."""
        if not isinstance(member_count, int) or isinstance(member_count, bool) or member_count < 1:
            raise InvalidParticipantMemberCountError(f"Participant member count must be an integer >= 1, got {member_count!r}.")
        return member_count

    @staticmethod
    def _resolve_display_name(display_name: str | None, name: PersonName | None) -> str:
        candidate = (display_name or "").strip() or (name.full_name if name is not None else "")
        if not candidate:
            raise InvalidPersonNameError("A participant must have a display name (or a structured name to derive one from).")
        return candidate

    @property
    def id(self) -> ParticipantId:
        return self._id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def name(self) -> PersonName | None:
        return self._name

    @property
    def birth_date(self) -> BirthDate | None:
        return self._birth_date

    @property
    def gender(self) -> Gender | None:
        return self._gender

    @property
    def registry_participant_id(self) -> RegistryParticipantId | None:
        return self._registry_participant_id

    @property
    def member_count(self) -> int:
        """How many people this entry represents: 1 for a solo, the headcount for a collective."""
        return self._member_count

    @property
    def identity_key(self) -> tuple[str, ...]:
        """The natural key used to detect duplicate participants in one submission.

        A registry-linked participant is keyed by its registry id (the same registry
        participant may not be added to one submission twice); a manually-entered one
        falls back to its display name plus birth date.
        """
        if self._registry_participant_id is not None:
            return ("registry", self._registry_participant_id.json())
        birth = self._birth_date.value.isoformat() if self._birth_date is not None else ""
        return ("person", self._display_name.casefold(), birth)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Participant) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Participant(id={self._id!r}, name={self._display_name!r})"


@dataclass(slots=True, eq=False, repr=False)
class Teacher:
    """A mentor credited on the submission, in a configurable role.

    Examples of roles: Teacher, Concertmaster, Choreographer, Director, Producer,
    Accompanist. The role is a configurable
    :class:`~apps.applications.domain.value_objects.TeacherRole` label, not a fixed
    enum.
    """

    _id: TeacherId
    _name: PersonName
    _role: TeacherRole
    _directory_teacher_id: DirectoryTeacherId | None = None

    @classmethod
    def create(
        cls,
        *,
        teacher_id: TeacherId,
        name: PersonName,
        role: TeacherRole,
        directory_teacher_id: DirectoryTeacherId | None = None,
    ) -> Teacher:
        return cls(_id=teacher_id, _name=name, _role=role, _directory_teacher_id=directory_teacher_id)

    @classmethod
    def rehydrate(
        cls,
        *,
        teacher_id: TeacherId,
        name: PersonName,
        role: TeacherRole,
        directory_teacher_id: DirectoryTeacherId | None = None,
    ) -> Teacher:
        return cls(_id=teacher_id, _name=name, _role=role, _directory_teacher_id=directory_teacher_id)

    @property
    def id(self) -> TeacherId:
        return self._id

    @property
    def name(self) -> PersonName:
        return self._name

    @property
    def role(self) -> TeacherRole:
        return self._role

    @property
    def directory_teacher_id(self) -> DirectoryTeacherId | None:
        return self._directory_teacher_id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Teacher) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Teacher(id={self._id!r}, name={self._name.full_name!r}, role={self._role.value!r})"


@dataclass(slots=True, eq=False, repr=False)
class Attachment:
    """A reference to a file supporting the submission (music, video, image, document).

    The domain stores only the :class:`~apps.applications.domain.value_objects.FileReference`
    and its :class:`~apps.applications.domain.value_objects.AttachmentType`; the
    file's bytes and storage are an infrastructure concern. An optional caption
    carries a human label.
    """

    _id: AttachmentId
    _type: AttachmentType
    _file: FileReference
    _caption: str | None = None

    @classmethod
    def create(cls, *, attachment_id: AttachmentId, attachment_type: AttachmentType, file: FileReference, caption: str | None = None) -> Attachment:
        return cls(_id=attachment_id, _type=attachment_type, _file=file, _caption=cls._clean_caption(caption))

    @classmethod
    def rehydrate(
        cls, *, attachment_id: AttachmentId, attachment_type: AttachmentType, file: FileReference, caption: str | None = None
    ) -> Attachment:
        return cls(_id=attachment_id, _type=attachment_type, _file=file, _caption=caption)

    @staticmethod
    def _clean_caption(caption: str | None) -> str | None:
        if caption is None:
            return None
        stripped = caption.strip()
        return stripped or None

    @property
    def id(self) -> AttachmentId:
        return self._id

    @property
    def type(self) -> AttachmentType:
        return self._type

    @property
    def file(self) -> FileReference:
        return self._file

    @property
    def caption(self) -> str | None:
        return self._caption

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Attachment) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Attachment(id={self._id!r}, type={self._type.value!r}, file={self._file.value!r})"


@dataclass(slots=True, eq=False, repr=False)
class Review:
    """One organizer review iteration - reviewer, comment and when it was made.

    Reviews form an append-only history (multiple iterations are supported); a
    review is immutable once created, so it exposes no mutators.
    """

    _id: ReviewId
    _reviewer_id: ReviewerId
    _comment: ReviewComment
    _created_at: datetime

    @classmethod
    def create(cls, *, review_id: ReviewId, reviewer_id: ReviewerId, comment: ReviewComment, created_at: datetime) -> Review:
        return cls(_id=review_id, _reviewer_id=reviewer_id, _comment=comment, _created_at=created_at)

    @classmethod
    def rehydrate(cls, *, review_id: ReviewId, reviewer_id: ReviewerId, comment: ReviewComment, created_at: datetime) -> Review:
        return cls(_id=review_id, _reviewer_id=reviewer_id, _comment=comment, _created_at=created_at)

    @property
    def id(self) -> ReviewId:
        return self._id

    @property
    def reviewer_id(self) -> ReviewerId:
        return self._reviewer_id

    @property
    def comment(self) -> ReviewComment:
        return self._comment

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Review) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Review(id={self._id!r}, reviewer={self._reviewer_id!r})"


# ===========================================================================
# Aggregate root
# ===========================================================================


@dataclass(slots=True, eq=False, repr=False)
class Submission:
    """The Submission aggregate root - one competitive performance for one competition.

    Guards its full lifecycle (``DRAFT -> SUBMITTED -> UNDER_REVIEW ->
    {APPROVED | REQUIRES_CORRECTION} -> WAITING_PAYMENT -> PAID -> ACCEPTED ->
    SCHEDULED -> COMPLETED``, plus ``CANCELLED`` until accepted) and every invariant
    of its content. Equality/hashing is by :class:`SubmissionId`.
    """

    _token: InitVar[object]
    _id: SubmissionId
    _competition_id: CompetitionId
    _applicant_id: UserId
    _status: SubmissionStatus
    _created_at: datetime
    _updated_at: datetime
    _performance: Performance | None = None
    _participants: dict[ParticipantId, Participant] = field(default_factory=dict)
    _teachers: dict[TeacherId, Teacher] = field(default_factory=dict)
    _attachments: dict[AttachmentId, Attachment] = field(default_factory=dict)
    _reviews: list[Review] = field(default_factory=list)
    _price_snapshot: PriceSnapshot | None = None
    _deleted_at: datetime | None = None
    _version: int = 1
    #: The version this aggregate was loaded at - the optimistic-concurrency
    #: pre-image the repository writes against. Transient (never persisted); a use
    #: case may bump ``_version`` several times before one save, so the pre-image
    #: must be the loaded version, not ``_version - 1``.
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "Submission must be created via Submission.draft() or Submission.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def draft(
        cls,
        *,
        submission_id: SubmissionId,
        competition_id: CompetitionId,
        applicant_id: UserId,
        now: datetime,
        performance: Performance | None = None,
    ) -> tuple[Submission, list[DomainEvent]]:
        """Create a brand-new submission in the DRAFT state.

        The only construction path for a new submission. Its content (performance,
        participants, teachers, attachments, price snapshot) starts empty and is
        built up with the ``add_*`` / ``set_*`` methods before :meth:`submit`.
        """
        submission = cls(
            _token=_CREATION_TOKEN,
            _id=submission_id,
            _competition_id=competition_id,
            _applicant_id=applicant_id,
            _status=SubmissionStatus.DRAFT,
            _created_at=now,
            _updated_at=now,
            _performance=performance,
        )
        events: list[DomainEvent] = [SubmissionCreated(aggregate_id=submission_id.value, competition_id=competition_id, applicant_id=applicant_id)]
        if performance is not None:
            events.append(PerformanceDefined(aggregate_id=submission_id.value))
        return submission, events

    @classmethod
    def rehydrate(
        cls,
        *,
        submission_id: SubmissionId,
        competition_id: CompetitionId,
        applicant_id: UserId,
        status: SubmissionStatus,
        created_at: datetime,
        updated_at: datetime,
        performance: Performance | None = None,
        participants: Sequence[Participant] = (),
        teachers: Sequence[Teacher] = (),
        attachments: Sequence[Attachment] = (),
        reviews: Sequence[Review] = (),
        price_snapshot: PriceSnapshot | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Submission:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=submission_id,
            _competition_id=competition_id,
            _applicant_id=applicant_id,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _performance=performance,
            _participants={p.id: p for p in participants},
            _teachers={t.id: t for t in teachers},
            _attachments={a.id: a for a in attachments},
            _reviews=list(reviews),
            _price_snapshot=price_snapshot,
            _deleted_at=deleted_at,
            _version=version,
            _initial_version=version,
        )

    # ------------------------------------------------------------------
    # Read-only views
    # ------------------------------------------------------------------

    @property
    def id(self) -> SubmissionId:
        return self._id

    @property
    def competition_id(self) -> CompetitionId:
        return self._competition_id

    @property
    def applicant_id(self) -> UserId:
        return self._applicant_id

    @property
    def status(self) -> SubmissionStatus:
        return self._status

    @property
    def performance(self) -> Performance | None:
        return self._performance

    @property
    def participants(self) -> tuple[Participant, ...]:
        return tuple(self._participants.values())

    @property
    def participant_count(self) -> int:
        """Total headcount across all entries - each solo counts as one, a collective as its member count."""
        return sum(participant.member_count for participant in self._participants.values())

    @property
    def teachers(self) -> tuple[Teacher, ...]:
        return tuple(self._teachers.values())

    @property
    def attachments(self) -> tuple[Attachment, ...]:
        return tuple(self._attachments.values())

    @property
    def reviews(self) -> tuple[Review, ...]:
        """The organizer review history, in the order it was recorded."""
        return tuple(self._reviews)

    @property
    def price_snapshot(self) -> PriceSnapshot | None:
        return self._price_snapshot

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def initial_version(self) -> int:
        """The version this aggregate was loaded at (the optimistic-concurrency pre-image)."""
        return self._initial_version

    @property
    def is_deleted(self) -> bool:
        return self._deleted_at is not None

    def is_draft(self) -> bool:
        return self._status is SubmissionStatus.DRAFT

    def is_editable(self) -> bool:
        """Whether content may currently be changed (DRAFT or REQUIRES_CORRECTION)."""
        return self._status in _EDITABLE_STATUSES

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def set_performance(self, *, performance: Performance, now: datetime) -> list[DomainEvent]:
        """Set or replace the submission's single performance (editable states only)."""
        self._ensure_editable()
        self._performance = performance
        self._touch(now)
        return [PerformanceDefined(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def add_participant(
        self,
        *,
        participant_id: ParticipantId,
        name: PersonName | None = None,
        birth_date: BirthDate | None = None,
        gender: Gender | None = None,
        display_name: str | None = None,
        registry_participant_id: RegistryParticipantId | None = None,
        member_count: int = 1,
        now: datetime,
    ) -> list[DomainEvent]:
        """Add a participant (a Participant Registry snapshot: solo or collective).

        ``member_count`` is the headcount this entry represents: 1 for a solo person,
        the number of people for a collective/ensemble - it drives the participant-count
        band check and per-participant pricing. Rejects a future birth date and a
        duplicate (the same registry participant, or - for manual entries - the same
        display name and birth date, already on this submission).
        """
        self._ensure_editable()
        if birth_date is not None and birth_date.value > now.date():
            raise InvalidBirthDateError(f"Birth date {birth_date} must not be in the future.")
        candidate = Participant.create(
            participant_id=participant_id,
            name=name,
            birth_date=birth_date,
            gender=gender,
            display_name=display_name,
            registry_participant_id=registry_participant_id,
            member_count=member_count,
        )
        if any(p.identity_key == candidate.identity_key for p in self._participants.values()):
            raise DuplicateParticipantError(f"Participant {candidate.display_name!r} is already in this submission.")
        self._participants[participant_id] = candidate
        self._touch(now)
        return [ParticipantAdded(aggregate_id=self._id.value, participant_id=participant_id)]

    def remove_participant(self, *, participant_id: ParticipantId, now: datetime) -> list[DomainEvent]:
        """Remove a participant.

        A DRAFT (or REQUIRES_CORRECTION) submission may be left temporarily without
        participants so the applicant can freely swap the sole one; the "at least one
        participant" invariant is enforced when the submission is submitted, not while
        it is being edited.
        """
        self._ensure_editable()
        if participant_id not in self._participants:
            raise ParticipantNotFoundError(f"No participant {participant_id} in this submission.")
        del self._participants[participant_id]
        self._touch(now)
        return [ParticipantRemoved(aggregate_id=self._id.value, participant_id=participant_id)]

    # ------------------------------------------------------------------
    # Teachers
    # ------------------------------------------------------------------

    def add_teacher(
        self,
        *,
        teacher_id: TeacherId,
        name: PersonName,
        role: TeacherRole,
        directory_teacher_id: DirectoryTeacherId | None = None,
        now: datetime,
    ) -> list[DomainEvent]:
        """Credit a teacher in a configurable role.

        ``directory_teacher_id`` links a teacher chosen from the reusable Teacher
        Directory; ``name``/``role`` are the immutable snapshot preserved on the
        submission so later directory edits never rewrite it.
        """
        self._ensure_editable()
        teacher = Teacher.create(teacher_id=teacher_id, name=name, role=role, directory_teacher_id=directory_teacher_id)
        self._teachers[teacher_id] = teacher
        self._touch(now)
        return [TeacherAdded(aggregate_id=self._id.value, teacher_id=teacher_id, role=role)]

    def remove_teacher(self, *, teacher_id: TeacherId, now: datetime) -> list[DomainEvent]:
        """Remove a teacher."""
        self._ensure_editable()
        if teacher_id not in self._teachers:
            raise TeacherNotFoundError(f"No teacher {teacher_id} in this submission.")
        del self._teachers[teacher_id]
        self._touch(now)
        return [TeacherRemoved(aggregate_id=self._id.value, teacher_id=teacher_id)]

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def add_attachment(
        self,
        *,
        attachment_id: AttachmentId,
        attachment_type: AttachmentType,
        file: FileReference,
        now: datetime,
        caption: str | None = None,
    ) -> list[DomainEvent]:
        """Add an attachment reference. Rejects duplicates (the same file referenced twice)."""
        self._ensure_editable()
        if any(a.file == file for a in self._attachments.values()):
            raise DuplicateAttachmentError(f"An attachment referencing {file.value!r} is already in this submission.")
        attachment = Attachment.create(attachment_id=attachment_id, attachment_type=attachment_type, file=file, caption=caption)
        self._attachments[attachment_id] = attachment
        self._touch(now)
        return [AttachmentAdded(aggregate_id=self._id.value, attachment_id=attachment_id, attachment_type=attachment_type)]

    def remove_attachment(self, *, attachment_id: AttachmentId, now: datetime) -> list[DomainEvent]:
        """Remove an attachment reference."""
        self._ensure_editable()
        if attachment_id not in self._attachments:
            raise AttachmentNotFoundError(f"No attachment {attachment_id} in this submission.")
        del self._attachments[attachment_id]
        self._touch(now)
        return [AttachmentRemoved(aggregate_id=self._id.value, attachment_id=attachment_id)]

    # ------------------------------------------------------------------
    # Price snapshot
    # ------------------------------------------------------------------

    def set_price_snapshot(self, *, price_snapshot: PriceSnapshot, now: datetime) -> list[DomainEvent]:
        """Freeze the immutable price snapshot onto the submission.

        Settable (and re-computable) only while the submission is editable; once it
        leaves the editable states the snapshot is permanent and further changes are
        refused so that later Competition pricing updates can never alter it.
        """
        if self._status not in _EDITABLE_STATUSES:
            raise PriceSnapshotLockedError(f"The price snapshot is frozen and cannot be changed while the submission is {self._status.value}.")
        self._price_snapshot = price_snapshot
        self._touch(now)
        return [
            PriceSnapshotCreated(
                aggregate_id=self._id.value,
                amount=str(price_snapshot.amount),
                currency=price_snapshot.currency,
                calculated_at=price_snapshot.calculated_at,
            )
        ]

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def add_review(
        self,
        *,
        review_id: ReviewId,
        reviewer_id: ReviewerId,
        comment: ReviewComment,
        now: datetime,
    ) -> list[DomainEvent]:
        """Record an organizer review iteration (allowed while SUBMITTED or UNDER_REVIEW)."""
        if self._status not in _REVIEWABLE_STATUSES:
            raise IllegalStatusTransitionError(f"A review cannot be recorded while the submission is {self._status.value}.")
        self._append_review(review_id=review_id, reviewer_id=reviewer_id, comment=comment, now=now)
        self._touch(now)
        return [ReviewAdded(aggregate_id=self._id.value, review_id=review_id, reviewer_id=reviewer_id)]

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def submit(self, *, policy: SubmissionParticipationPolicy, now: datetime) -> list[DomainEvent]:
        """Submit the submission to the competition.

        Enforces the submission invariants: a performance exists, at least one
        participant exists, an immutable price snapshot exists, the performance's
        combination is admissible, and the participant count matches the configured
        participant group's band (validated against the supplied read-model
        ``policy`` - never by importing the Competition aggregate).
        """
        self._assert_submittable(policy)
        previous = self._status
        self._transition_to(SubmissionStatus.SUBMITTED, now=now)
        return [SubmissionSubmitted(aggregate_id=self._id.value, previous_status=previous)]

    def begin_review(self, *, now: datetime) -> list[DomainEvent]:
        """Begin reviewing the submission (SUBMITTED -> UNDER_REVIEW)."""
        self._transition_to(SubmissionStatus.UNDER_REVIEW, now=now)
        return [SubmissionReviewStarted(aggregate_id=self._id.value)]

    def return_for_correction(
        self,
        *,
        review_id: ReviewId,
        reviewer_id: ReviewerId,
        comment: ReviewComment,
        now: datetime,
    ) -> list[DomainEvent]:
        """Return the submission for correction, recording the review that explains why.

        The review comment is mandatory: a correction request must tell the
        applicant what to fix.
        """
        self._append_review(review_id=review_id, reviewer_id=reviewer_id, comment=comment, now=now)
        self._transition_to(SubmissionStatus.REQUIRES_CORRECTION, now=now)
        return [
            ReviewAdded(aggregate_id=self._id.value, review_id=review_id, reviewer_id=reviewer_id),
            SubmissionReturnedForCorrection(aggregate_id=self._id.value, review_id=review_id),
        ]

    def approve(self, *, now: datetime) -> list[DomainEvent]:
        """Approve the submission (UNDER_REVIEW -> APPROVED)."""
        self._transition_to(SubmissionStatus.APPROVED, now=now)
        return [SubmissionApproved(aggregate_id=self._id.value)]

    def await_payment(self, *, now: datetime) -> list[DomainEvent]:
        """Move the approved submission to awaiting payment (APPROVED -> WAITING_PAYMENT)."""
        self._transition_to(SubmissionStatus.WAITING_PAYMENT, now=now)
        return [SubmissionAwaitingPayment(aggregate_id=self._id.value)]

    def mark_paid(self, *, now: datetime) -> list[DomainEvent]:
        """Mark the fee as paid (WAITING_PAYMENT -> PAID)."""
        self._transition_to(SubmissionStatus.PAID, now=now)
        return [SubmissionPaid(aggregate_id=self._id.value)]

    def accept(self, *, now: datetime) -> list[DomainEvent]:
        """Accept the submission into the competition (PAID -> ACCEPTED).

        From here content is permanently frozen and the submission can no longer be
        cancelled - it is committed to the running order.
        """
        self._transition_to(SubmissionStatus.ACCEPTED, now=now)
        return [SubmissionAccepted(aggregate_id=self._id.value)]

    def schedule(self, *, now: datetime) -> list[DomainEvent]:
        """Assign the submission a slot in the running order (ACCEPTED -> SCHEDULED)."""
        self._transition_to(SubmissionStatus.SCHEDULED, now=now)
        return [SubmissionScheduled(aggregate_id=self._id.value)]

    def complete(self, *, now: datetime) -> list[DomainEvent]:
        """Mark the performance as having taken place (SCHEDULED -> COMPLETED)."""
        self._transition_to(SubmissionStatus.COMPLETED, now=now)
        return [SubmissionCompleted(aggregate_id=self._id.value)]

    def cancel(self, *, now: datetime) -> list[DomainEvent]:
        """Cancel the submission (withdraw or reject). Not possible once ACCEPTED."""
        previous = self._status
        self._transition_to(SubmissionStatus.CANCELLED, now=now)
        return [SubmissionCancelled(aggregate_id=self._id.value, previous_status=previous)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_review(self, *, review_id: ReviewId, reviewer_id: ReviewerId, comment: ReviewComment, now: datetime) -> None:
        review = Review.create(review_id=review_id, reviewer_id=reviewer_id, comment=comment, created_at=now)
        self._reviews.append(review)

    def _assert_submittable(self, policy: SubmissionParticipationPolicy) -> None:
        """Assert every invariant required before the submission may be submitted."""
        if self._performance is None:
            raise PerformanceRequiredError("A submission must have a performance before it can be submitted.")
        if not self._participants:
            raise ParticipantRequiredError("A submission must have at least one participant before it can be submitted.")
        if self._price_snapshot is None:
            raise PriceSnapshotRequiredError("A submission must have an immutable price snapshot before it can be submitted.")
        if not policy.is_admissible:
            raise CombinationNotAdmissibleError("The performance's configuration combination is not admissible in this competition.")
        if not policy.allows_participant_count(self.participant_count):
            raise ParticipantCountMismatchError(
                f"Participant count {self.participant_count} does not match the configured group range {policy.participant_count_range}."
            )
        if policy.requires_teacher and not self._teachers:
            raise TeacherRequiredError("This competition requires a teacher to be credited before the submission can be submitted.")
        present_types = {attachment.type for attachment in self._attachments.values()}
        missing = policy.required_attachment_types() - present_types
        if missing:
            kinds = ", ".join(sorted(kind.value for kind in missing))
            raise RequiredAttachmentMissingError(f"This competition requires the following uploads before submission: {kinds}.")

    def _ensure_editable(self) -> None:
        if self._status not in _EDITABLE_STATUSES:
            raise SubmissionNotEditableError(
                f"Submission content can only be changed while DRAFT or REQUIRES_CORRECTION, not while {self._status.value}."
            )

    def _transition_to(self, target: SubmissionStatus, *, now: datetime) -> None:
        """Move to ``target`` if the transition is legal from the current status."""
        if target not in _LEGAL_TRANSITIONS[self._status]:
            raise IllegalStatusTransitionError(f"Cannot transition from {self._status.value} to {target.value}.")
        self._status = target
        self._touch(now)

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def mark_persisted(self) -> None:
        """Mark this in-memory instance as clean at its current version.

        Called by the repository after a successful write so the next save uses the
        just-persisted version as its optimistic-concurrency pre-image. This lets one
        use case bump the version several times before a single save, and lets the
        same instance be saved more than once, without a false conflict.
        """
        self._initial_version = self._version

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Submission) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Submission(id={self._id!r}, status={self._status.value!r}, participants={len(self._participants)})"


# ===========================================================================
# Application aggregate root (the order grouping one applicant's submissions)
# ===========================================================================
#
# The **Application** is a *second, independent* aggregate root in this bounded
# context. It is the order the applicant places for one competition: it groups
# their Submissions, owns the educational-organization reference, the selected
# additional services, the recorded consents, the immutable total price and the
# payment state, and guards the order-level lifecycle.
#
# It references its Submissions **by id only** - it never contains or imports a
# Submission object. Each reference caches a display snapshot
# (:class:`~apps.applications.domain.value_objects.SubmissionRef`) refreshed by an
# application-layer projection reacting to Submission events, so listing an order
# never touches Submission storage. Crucially, the Application does **not** run its
# own review workflow: approval lives on the Submissions, and the order *derives*
# its readiness for payment from their cached statuses (all approved -> payable).

#: The order-lifecycle transitions the Application permits. ``COMPLETED`` and
#: ``CANCELLED`` are terminal. Cancellation is possible until payment settles.
_LEGAL_APPLICATION_TRANSITIONS: Final[dict[ApplicationStatus, frozenset[ApplicationStatus]]] = {
    ApplicationStatus.DRAFT: frozenset({ApplicationStatus.SUBMITTED, ApplicationStatus.CANCELLED}),
    ApplicationStatus.SUBMITTED: frozenset({ApplicationStatus.WAITING_PAYMENT, ApplicationStatus.CANCELLED}),
    ApplicationStatus.WAITING_PAYMENT: frozenset({ApplicationStatus.PAID, ApplicationStatus.CANCELLED}),
    ApplicationStatus.PAID: frozenset({ApplicationStatus.COMPLETED}),
    ApplicationStatus.COMPLETED: frozenset(),
    ApplicationStatus.CANCELLED: frozenset(),
}

#: The only status in which the order's composition (educational organization,
#: submission references, additional services, consents) may be edited.
_APPLICATION_EDITABLE_STATUSES: Final = frozenset({ApplicationStatus.DRAFT})

#: Statuses in which the applicant may attach (or replace) the payment receipt:
#: any time before the order is settled. Some festivals require payment upfront, so
#: a receipt may be uploaded while the order is still a DRAFT in the wizard, through
#: submission and while awaiting payment; a paid/completed/cancelled order is settled.
_APPLICATION_RECEIPT_STATUSES: Final = frozenset(
    {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, ApplicationStatus.WAITING_PAYMENT}
)

#: Statuses in which a submission reference's cached snapshot may still be
#: refreshed by the projection. Past payment the order is settled and its lines
#: are historical, so refreshes are ignored rather than mutating a settled order.
_APPLICATION_REFRESHABLE_STATUSES: Final = frozenset({ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, ApplicationStatus.WAITING_PAYMENT})


@dataclass(slots=True, eq=False, repr=False)
class Application:
    """The Application aggregate root - the order grouping one applicant's submissions.

    Guards the order lifecycle (``DRAFT -> SUBMITTED -> WAITING_PAYMENT -> PAID ->
    COMPLETED``, plus ``CANCELLED`` until payment) and the order-level invariants
    (at least one submission and every required consent before it may be submitted;
    all submissions approved before it may be billed). Equality/hashing is by
    :class:`ApplicationId`.
    """

    _token: InitVar[object]
    _id: ApplicationId
    _competition_id: CompetitionId
    _applicant_id: UserId
    _status: ApplicationStatus
    _created_at: datetime
    _updated_at: datetime
    _educational_organization_id: EducationalOrganizationId | None = None
    _organization_name: OrganizationName | None = None
    _submission_refs: dict[SubmissionId, SubmissionRef] = field(default_factory=dict)
    _service_lines: dict[ServiceId, ServiceLine] = field(default_factory=dict)
    _consents: tuple[Consent, ...] = ()
    _total_price: TotalPriceSnapshot | None = None
    _status_history: list[ApplicationStatusChange] = field(default_factory=list)
    _payment_receipt: PaymentReceipt | None = None
    _paid_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1
    #: The version this aggregate was loaded at - the optimistic-concurrency
    #: pre-image the repository writes against. Transient (never persisted); a use
    #: case may bump ``_version`` several times before one save, so the pre-image
    #: must be the loaded version, not ``_version - 1``.
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectApplicationConstructionError(
                "Application must be created via Application.create() or Application.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        application_id: ApplicationId,
        competition_id: CompetitionId,
        applicant_id: UserId,
        now: datetime,
    ) -> tuple[Application, list[DomainEvent]]:
        """Create a brand-new empty application (order) in the DRAFT state."""
        application = cls(
            _token=_CREATION_TOKEN,
            _id=application_id,
            _competition_id=competition_id,
            _applicant_id=applicant_id,
            _status=ApplicationStatus.DRAFT,
            _created_at=now,
            _updated_at=now,
            _total_price=cls._zero_total(now),
            _status_history=[ApplicationStatusChange(from_status=None, to_status=ApplicationStatus.DRAFT, occurred_at=now)],
        )
        events: list[DomainEvent] = [ApplicationCreated(aggregate_id=application_id.value, competition_id=competition_id, applicant_id=applicant_id)]
        return application, events

    @classmethod
    def rehydrate(
        cls,
        *,
        application_id: ApplicationId,
        competition_id: CompetitionId,
        applicant_id: UserId,
        status: ApplicationStatus,
        created_at: datetime,
        updated_at: datetime,
        educational_organization_id: EducationalOrganizationId | None = None,
        organization_name: OrganizationName | None = None,
        submission_refs: Sequence[SubmissionRef] = (),
        service_lines: Sequence[ServiceLine] = (),
        consents: Sequence[Consent] = (),
        total_price: TotalPriceSnapshot | None = None,
        status_history: Sequence[ApplicationStatusChange] = (),
        payment_receipt: PaymentReceipt | None = None,
        paid_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Application:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=application_id,
            _competition_id=competition_id,
            _applicant_id=applicant_id,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _educational_organization_id=educational_organization_id,
            _organization_name=organization_name,
            _submission_refs={ref.submission_id: ref for ref in submission_refs},
            _service_lines={line.service_id: line for line in service_lines},
            _consents=tuple(consents),
            _total_price=total_price,
            _status_history=list(status_history),
            _payment_receipt=payment_receipt,
            _paid_at=paid_at,
            _deleted_at=deleted_at,
            _version=version,
            _initial_version=version,
        )

    # ------------------------------------------------------------------
    # Read-only views
    # ------------------------------------------------------------------

    @property
    def id(self) -> ApplicationId:
        return self._id

    @property
    def competition_id(self) -> CompetitionId:
        return self._competition_id

    @property
    def applicant_id(self) -> UserId:
        return self._applicant_id

    @property
    def status(self) -> ApplicationStatus:
        return self._status

    @property
    def educational_organization_id(self) -> EducationalOrganizationId | None:
        return self._educational_organization_id

    @property
    def organization_name(self) -> OrganizationName | None:
        return self._organization_name

    @property
    def submission_refs(self) -> tuple[SubmissionRef, ...]:
        return tuple(self._submission_refs.values())

    @property
    def submission_count(self) -> int:
        return len(self._submission_refs)

    @property
    def service_lines(self) -> tuple[ServiceLine, ...]:
        return tuple(self._service_lines.values())

    @property
    def consents(self) -> tuple[Consent, ...]:
        return self._consents

    @property
    def total_price(self) -> TotalPriceSnapshot | None:
        return self._total_price

    @property
    def status_history(self) -> tuple[ApplicationStatusChange, ...]:
        """The order's status history, in the order it was recorded."""
        return tuple(self._status_history)

    @property
    def payment_receipt(self) -> PaymentReceipt | None:
        return self._payment_receipt

    @property
    def paid_at(self) -> datetime | None:
        return self._paid_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def initial_version(self) -> int:
        """The version this aggregate was loaded at (the optimistic-concurrency pre-image)."""
        return self._initial_version

    @property
    def is_deleted(self) -> bool:
        return self._deleted_at is not None

    def is_draft(self) -> bool:
        return self._status is ApplicationStatus.DRAFT

    def is_editable(self) -> bool:
        """Whether the order's composition may currently be changed (DRAFT only)."""
        return self._status in _APPLICATION_EDITABLE_STATUSES

    def is_ready_for_payment(self) -> bool:
        """Whether every referenced submission is approved (the derived payment gate)."""
        return bool(self._submission_refs) and all(ref.is_approved for ref in self._submission_refs.values())

    def accepts_payment_receipt(self) -> bool:
        """Whether a payment receipt may currently be attached (any time before settled)."""
        return self._status in _APPLICATION_RECEIPT_STATUSES

    # ------------------------------------------------------------------
    # Composition (editable in DRAFT only)
    # ------------------------------------------------------------------

    def select_educational_organization(
        self,
        *,
        educational_organization_id: EducationalOrganizationId,
        organization_name: OrganizationName,
        now: datetime,
    ) -> list[DomainEvent]:
        """Select (or change) the educational organization, freezing its display name."""
        self._ensure_editable()
        self._educational_organization_id = educational_organization_id
        self._organization_name = organization_name
        self._touch(now)
        return [EducationalOrganizationSelected(aggregate_id=self._id.value, educational_organization_id=educational_organization_id)]

    def attach_submission(self, *, ref: SubmissionRef, now: datetime) -> list[DomainEvent]:
        """Attach a submission reference to the order (add a performance to it)."""
        self._ensure_editable()
        if ref.submission_id in self._submission_refs:
            raise DuplicateSubmissionRefError(f"Submission {ref.submission_id.json()} is already attached to this application.")
        self._submission_refs[ref.submission_id] = ref
        self._recalculate_total(now)
        self._touch(now)
        return [SubmissionAttachedToApplication(aggregate_id=self._id.value, submission_id=ref.submission_id)]

    def detach_submission(self, *, submission_id: SubmissionId, now: datetime) -> list[DomainEvent]:
        """Remove a submission reference from the order (draft only).

        Detaching only drops the *reference* from the order; the underlying
        Submission is never physically deleted here - the application layer archives
        or cancels it through its own aggregate. The order simply stops billing it.
        """
        self._ensure_editable()
        if submission_id not in self._submission_refs:
            raise SubmissionRefNotFoundError(f"Submission {submission_id.json()} is not attached to this application.")
        del self._submission_refs[submission_id]
        self._recalculate_total(now)
        self._touch(now)
        return [SubmissionDetachedFromApplication(aggregate_id=self._id.value, submission_id=submission_id)]

    def refresh_submission_ref(self, *, ref: SubmissionRef, now: datetime) -> list[DomainEvent]:
        """Refresh the cached snapshot of an attached submission (projection hook).

        Called by the application-layer projection when a referenced submission
        changes (priced, approved, returned for correction, ...). It updates the
        cached status/price/display, and recomputes the order total **only while the
        order is still a draft** - once submitted the total is frozen and a later
        submission change must never move it. Refreshes past payment are ignored.
        """
        if self._status not in _APPLICATION_REFRESHABLE_STATUSES:
            return []
        if ref.submission_id not in self._submission_refs:
            raise SubmissionRefNotFoundError(f"Submission {ref.submission_id.json()} is not attached to this application.")
        self._submission_refs[ref.submission_id] = ref
        if self._status is ApplicationStatus.DRAFT:
            self._recalculate_total(now)
        self._touch(now)
        return []

    def add_service(self, *, service_line: ServiceLine, now: datetime) -> list[DomainEvent]:
        """Select an additional service on the order."""
        self._ensure_editable()
        if service_line.service_id in self._service_lines:
            raise DuplicateServiceLineError(f"Service {service_line.service_id.json()} is already selected on this application.")
        self._service_lines[service_line.service_id] = service_line
        self._recalculate_total(now)
        self._touch(now)
        return [AdditionalServiceSelected(aggregate_id=self._id.value, service_id=service_line.service_id)]

    def remove_service(self, *, service_id: ServiceId, now: datetime) -> list[DomainEvent]:
        """Remove a previously selected additional service from the order."""
        self._ensure_editable()
        if service_id not in self._service_lines:
            raise ServiceLineNotFoundError(f"Service {service_id.json()} is not selected on this application.")
        del self._service_lines[service_id]
        self._recalculate_total(now)
        self._touch(now)
        return [AdditionalServiceRemoved(aggregate_id=self._id.value, service_id=service_id)]

    def record_consents(self, *, consents: Sequence[Consent], now: datetime) -> list[DomainEvent]:
        """Record the set of accepted consents (replaces any previously recorded set)."""
        self._ensure_editable()
        self._consents = tuple(consents)
        self._touch(now)
        return [ConsentsRecorded(aggregate_id=self._id.value, consent_count=len(self._consents))]

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def submit(
        self,
        *,
        required_consent_codes: frozenset[str] = frozenset(),
        required_service_ids: frozenset[str] = frozenset(),
        now: datetime,
    ) -> list[DomainEvent]:
        """Submit the order (DRAFT -> SUBMITTED), freezing its total price.

        Enforces the order invariants: at least one submission is attached, every
        consent the competition requires has been recorded, and every additional
        service the competition mandates has been selected. The total price is
        recomputed once and then frozen - future Competition pricing changes can
        never alter an order already placed. Submitting the individual Submissions
        for review is an application-layer concern (orchestrated over their own
        aggregate); this transition governs only the order.
        """
        if not self._submission_refs:
            raise NoSubmissionsError("An application must reference at least one submission before it can be submitted.")
        recorded = {consent.code for consent in self._consents}
        missing_consents = required_consent_codes - recorded
        if missing_consents:
            raise MissingRequiredConsentError(f"The following required consents were not recorded: {', '.join(sorted(missing_consents))}.")
        selected_services = {line.service_id.json() for line in self._service_lines.values()}
        missing_services = required_service_ids - selected_services
        if missing_services:
            raise MissingRequiredServiceError(f"The following required services were not selected: {', '.join(sorted(missing_services))}.")
        total = self._recalculate_total(now)
        self._transition_to(ApplicationStatus.SUBMITTED, now=now)
        return [ApplicationSubmitted(aggregate_id=self._id.value, amount=str(total.amount), currency=total.currency)]

    def request_payment(self, *, now: datetime) -> list[DomainEvent]:
        """Move the order to awaiting payment (SUBMITTED -> WAITING_PAYMENT).

        The derived readiness gate: allowed only once **every** referenced
        submission is approved. Readiness is read from the cached submission
        statuses (kept fresh by the projection); the Application never runs its own
        review.
        """
        if not self.is_ready_for_payment():
            raise NotAllSubmissionsApprovedError("The application is not ready for payment: not all submissions are approved.")
        self._transition_to(ApplicationStatus.WAITING_PAYMENT, now=now)
        return [ApplicationAwaitingPayment(aggregate_id=self._id.value)]

    def upload_payment_receipt(self, *, file: FileReference, now: datetime) -> list[DomainEvent]:
        """Attach (or replace) the applicant's proof of payment for the order.

        Allowed any time before the order is settled (``DRAFT``, ``SUBMITTED`` or
        ``WAITING_PAYMENT``) - festivals that require upfront payment let the applicant
        attach the receipt while still filling in the draft; a paid/closed order is
        final. This does not change the order status; the organizer still confirms
        payment separately. Re-uploading replaces the previous receipt.
        """
        if self._status not in _APPLICATION_RECEIPT_STATUSES:
            raise PaymentReceiptNotAllowedError(
                f"A payment receipt cannot be attached once the application is settled ({self._status.value})."
            )
        self._payment_receipt = PaymentReceipt(file=file, uploaded_at=now)
        self._touch(now)
        return [PaymentReceiptUploaded(aggregate_id=self._id.value)]

    def mark_paid(self, *, now: datetime) -> list[DomainEvent]:
        """Record that the order's total was paid (WAITING_PAYMENT -> PAID)."""
        self._transition_to(ApplicationStatus.PAID, now=now)
        self._paid_at = now
        return [ApplicationPaid(aggregate_id=self._id.value)]

    def complete(self, *, now: datetime) -> list[DomainEvent]:
        """Mark the order as fully settled (PAID -> COMPLETED)."""
        self._transition_to(ApplicationStatus.COMPLETED, now=now)
        return [ApplicationCompleted(aggregate_id=self._id.value)]

    def cancel(self, *, now: datetime) -> list[DomainEvent]:
        """Cancel the order (withdraw or reject). Not possible once paid."""
        previous = self._status
        self._transition_to(ApplicationStatus.CANCELLED, now=now)
        return [ApplicationCancelled(aggregate_id=self._id.value, previous_status=previous)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _zero_total(now: datetime) -> TotalPriceSnapshot:
        zero = Money.of("0.00", Currency.BYN)
        return TotalPriceSnapshot(total=zero, submissions_total=zero, services_total=zero, calculated_at=now)

    def _recalculate_total(self, now: datetime) -> TotalPriceSnapshot:
        """Recompute and freeze the total = sum of submission price lines + sum of service lines.

        Called only while the order is a draft (submit calls it while still DRAFT,
        before transitioning), so the frozen total can never shift under a placed
        order; calling it after the order leaves DRAFT is refused. All money is
        single-currency (``BYN``) today.
        """
        if self._status not in _APPLICATION_EDITABLE_STATUSES:
            raise TotalPriceLockedError(f"The total price is frozen and cannot be recomputed while the application is {self._status.value}.")
        currency = Currency.BYN
        submissions_amount = sum((ref.price_line.amount for ref in self._submission_refs.values()), Decimal("0"))
        services_amount = sum((line.line_total.amount for line in self._service_lines.values()), Decimal("0"))
        total = TotalPriceSnapshot(
            total=Money.of(submissions_amount + services_amount, currency),
            submissions_total=Money.of(submissions_amount, currency),
            services_total=Money.of(services_amount, currency),
            calculated_at=now,
        )
        self._total_price = total
        return total

    def _ensure_editable(self) -> None:
        if self._status not in _APPLICATION_EDITABLE_STATUSES:
            raise ApplicationNotEditableError(f"An application's composition can only be changed while DRAFT, not while {self._status.value}.")

    def _transition_to(self, target: ApplicationStatus, *, now: datetime) -> None:
        """Move to ``target`` if the transition is legal, recording it in the history."""
        if target not in _LEGAL_APPLICATION_TRANSITIONS[self._status]:
            raise IllegalApplicationStatusTransitionError(f"Cannot transition from {self._status.value} to {target.value}.")
        previous = self._status
        self._status = target
        self._status_history.append(ApplicationStatusChange(from_status=previous, to_status=target, occurred_at=now))
        self._touch(now)

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def mark_persisted(self) -> None:
        """Mark this in-memory instance as clean at its current version.

        Called by the repository after a successful write so the next save uses the
        just-persisted version as its optimistic-concurrency pre-image. This lets one
        use case bump the version several times before a single save, and lets the
        same instance be saved more than once, without a false conflict.
        """
        self._initial_version = self._version

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Application) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Application(id={self._id!r}, status={self._status.value!r}, submissions={len(self._submission_refs)})"


__all__ = [
    "Application",
    "Attachment",
    "Participant",
    "Review",
    "Submission",
    "Teacher",
]
