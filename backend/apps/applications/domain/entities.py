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

from collections.abc import Collection, Sequence
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
    ParticipantMemberCountChanged,
    ParticipantMembersChanged,
    ParticipantRemoved,
    PayerRecorded,
    PaymentReceiptRemoved,
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
    AgeCompositionRequiredError,
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
    InvalidCollectiveMemberError,
    InvalidParticipantMemberCountError,
    InvalidPersonNameError,
    MissingRequiredConsentError,
    MissingRequiredServiceError,
    NoSubmissionsError,
    NotAllSubmissionsApprovedError,
    ParticipantCommentNotAcceptedError,
    ParticipantCountMismatchError,
    ParticipantNotFoundError,
    ParticipantRequiredError,
    PayerRequiredError,
    PaymentReceiptNotAllowedError,
    PaymentReceiptNotFoundError,
    PerformanceRequiredError,
    PriceSnapshotLockedError,
    PriceSnapshotRequiredError,
    RequiredAttachmentMissingError,
    ServiceLineNotFoundError,
    SubmissionNotEditableError,
    SubmissionRefNotFoundError,
    TeacherNotFoundError,
    TeacherRequiredError,
    TooManyPaymentReceiptsError,
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
    PaymentReceiptId,
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
    SubmissionStatusChange,
    TeacherId,
    TeacherRole,
    TotalPriceSnapshot,
    UserId,
)

_CREATION_TOKEN: Final = object()

#: The lifecycle transitions the aggregate permits. ``COMPLETED`` and ``CANCELLED``
#: are terminal. Cancellation stays possible while the submission is committed to
#: the running order (``ACCEPTED``, ``SCHEDULED``) but only by organizer decision —
#: see :data:`_ORGANIZER_ONLY_CANCELLABLE_STATUSES`.
_LEGAL_TRANSITIONS: Final[dict[SubmissionStatus, frozenset[SubmissionStatus]]] = {
    SubmissionStatus.DRAFT: frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.SUBMITTED: frozenset({SubmissionStatus.UNDER_REVIEW, SubmissionStatus.CANCELLED}),
    SubmissionStatus.UNDER_REVIEW: frozenset({SubmissionStatus.APPROVED, SubmissionStatus.REQUIRES_CORRECTION, SubmissionStatus.CANCELLED}),
    SubmissionStatus.REQUIRES_CORRECTION: frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.APPROVED: frozenset({SubmissionStatus.WAITING_PAYMENT, SubmissionStatus.CANCELLED}),
    SubmissionStatus.WAITING_PAYMENT: frozenset({SubmissionStatus.PAID, SubmissionStatus.CANCELLED}),
    SubmissionStatus.PAID: frozenset({SubmissionStatus.ACCEPTED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.ACCEPTED: frozenset({SubmissionStatus.SCHEDULED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.SCHEDULED: frozenset({SubmissionStatus.COMPLETED, SubmissionStatus.CANCELLED}),
    SubmissionStatus.COMPLETED: frozenset(),
    SubmissionStatus.CANCELLED: frozenset(),
}

#: Statuses a submission can only be cancelled *out of* by organizer decision.
#:
#: Once an entry is committed to the running order the applicant can no longer
#: withdraw it — the fee is settled, the slot is allocated and the programme is being
#: built around it. The organizer still can, because a withdrawal at this point is
#: decided case by case: a disqualification, a no-show, or an applicant's request
#: granted as an exception. Making it an organizer action is what keeps it a decision
#: rather than a self-service button.
#:
#: ``COMPLETED`` is absent deliberately: the performance took place, so cancelling it
#: would rewrite history — and its diploma may already be in the register.
_ORGANIZER_ONLY_CANCELLABLE_STATUSES: Final = frozenset({SubmissionStatus.ACCEPTED, SubmissionStatus.SCHEDULED})

#: Statuses in which the submission's content (performance, participants, teachers,
#: attachments, price snapshot) may still be edited. Beyond these it is frozen.
_EDITABLE_STATUSES: Final = frozenset({SubmissionStatus.DRAFT, SubmissionStatus.SUBMITTED, SubmissionStatus.REQUIRES_CORRECTION})

#: Statuses in which the organizer may record a review iteration.
_REVIEWABLE_STATUSES: Final = frozenset({SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW})

#: Attachment kinds that outlive the content freeze.
#:
#: A backing track is not a claim about the entry — it is the material the act is
#: performed to, and it is wanted right up to the day. The competition already has a
#: deadline of its own for it (``MUSIC_UPLOAD``), deliberately later than the
#: application deadline, and a running order is built only from entries that are
#: ``ACCEPTED`` or beyond. Freezing the track together with the content therefore made
#: that deadline unreachable: by the time an entry could take a slot in the programme,
#: nobody — not the applicant, not the organizer — could put a phonogram on it, and the
#: sound desk's archive came out empty. Everything else (participants, teachers, the
#: performance itself, benefit paperwork) stays frozen: those are the entry's content,
#: and the organizer accepted *that*.
_LATE_ATTACHMENT_TYPES: Final = frozenset({AttachmentType.MUSIC})

#: How each kind of file is named to the applicant. The enum's own values are wire
#: codes; a person is told «фонограмма», not ``MUSIC``.
_ATTACHMENT_LABELS_RU: Final[dict[AttachmentType, str]] = {
    AttachmentType.MUSIC: "фонограмма",
    AttachmentType.VIDEO: "видео",
    AttachmentType.IMAGE: "фотография",
    AttachmentType.DOCUMENT: "документ",
    AttachmentType.BENEFIT: "документ на льготу",
}

#: Statuses in which a late attachment kind may still be added or removed: the entry is
#: live. ``COMPLETED`` and ``CANCELLED`` are out — the performance took place, or there
#: will not be one, and in both cases there is nothing left to cue.
_LIVE_STATUSES: Final = frozenset(
    {
        SubmissionStatus.DRAFT,
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.UNDER_REVIEW,
        SubmissionStatus.REQUIRES_CORRECTION,
        SubmissionStatus.APPROVED,
        SubmissionStatus.WAITING_PAYMENT,
        SubmissionStatus.PAID,
        SubmissionStatus.ACCEPTED,
        SubmissionStatus.SCHEDULED,
    }
)

#: Longest ФИО a collective may list for one of its members. Generous: it is printed
#: on a diploma, so a long double-barrelled name must fit rather than be truncated.
_MAX_MEMBER_NAME_LENGTH: Final = 200

#: Most people one collective may name. Well above any real ensemble (a large choir
#: is ~100), and low enough that a runaway client cannot ask for ten thousand
#: individual diplomas in one publication.
_MAX_COLLECTIVE_MEMBERS: Final = 200


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

    A collective may also name the people in it (:attr:`members`) - see
    :meth:`_normalize_members`. The roster is optional and exists for one purpose:
    the applicant who fills it in gets an individual diploma per named person on top
    of the collective's own.
    """

    _id: ParticipantId
    _display_name: str
    _name: PersonName | None = None
    _birth_date: BirthDate | None = None
    _gender: Gender | None = None
    _registry_participant_id: RegistryParticipantId | None = None
    _member_count: int = 1
    _members: tuple[str, ...] = ()

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
        members: Sequence[str] = (),
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
            _members=cls._normalize_members(members),
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
        members: Sequence[str] = (),
    ) -> Participant:
        return cls(
            _id=participant_id,
            _display_name=cls._resolve_display_name(display_name, name),
            _name=name,
            _birth_date=birth_date,
            _gender=gender,
            _registry_participant_id=registry_participant_id,
            _member_count=cls._validate_member_count(member_count),
            _members=cls._normalize_members(members),
        )

    @staticmethod
    def _validate_member_count(member_count: int) -> int:
        """A solo entry counts as one; a collective carries its headcount (>= 1)."""
        if not isinstance(member_count, int) or isinstance(member_count, bool) or member_count < 1:
            raise InvalidParticipantMemberCountError(f"Participant member count must be an integer >= 1, got {member_count!r}.")
        return member_count

    @staticmethod
    def _normalize_members(members: Sequence[str]) -> tuple[str, ...]:
        """The roster as it will be printed: trimmed, blank-free and de-duplicated.

        Blank rows are dropped rather than rejected, because the form the applicant
        fills in has spare rows in it by design. Duplicates are dropped because an
        individual document is identified by the person it names - two identical
        names on one entry would be one document, so accepting both would silently
        promise a diploma that cannot exist. Order is the applicant's own.
        """
        roster: list[str] = []
        seen: set[str] = set()
        for raw in members:
            name = " ".join(str(raw).split())
            if not name:
                continue
            if len(name) > _MAX_MEMBER_NAME_LENGTH:
                raise InvalidCollectiveMemberError(f"Member name must be at most {_MAX_MEMBER_NAME_LENGTH} characters, got {len(name)}.")
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            roster.append(name)
        if len(roster) > _MAX_COLLECTIVE_MEMBERS:
            raise InvalidCollectiveMemberError(f"A collective may name at most {_MAX_COLLECTIVE_MEMBERS} members, got {len(roster)}.")
        return tuple(roster)

    def with_member_count(self, member_count: int) -> None:
        """Replace the headcount in place (aggregate-internal; the root calls this).

        Same reasoning as :meth:`with_members`: how many people stand on stage is a
        fact about this entry, not a different entry, so the id the client holds -
        and with it the roster already typed against it - survives the correction.
        """
        self._member_count = self._validate_member_count(member_count)

    def with_members(self, members: Sequence[str]) -> None:
        """Replace the roster in place (aggregate-internal; the root calls this).

        Mutating rather than returning a copy keeps the participant's identity - and
        with it the id the client holds and the duplicate rule - untouched: naming the
        people in a collective is not a different participant.
        """
        self._members = self._normalize_members(members)

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
    def members(self) -> tuple[str, ...]:
        """The named people in a collective, in the applicant's own order.

        Empty for a solo, and empty for a collective whose applicant did not ask for
        individual documents - naming the roster is what asks for them.
        """
        return self._members

    @property
    def wants_individual_documents(self) -> bool:
        """Whether this entry asked for a document per named person.

        The roster *is* the request: there is no separate flag to fall out of step
        with it, so "opted in with nobody named" cannot happen.
        """
        return bool(self._members)

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

    ``size_bytes`` is the exception to "no file detail here", and it earns its place: the
    media ceiling applies to the *sum* of a performance's files, so the aggregate has to
    be able to answer how much has already been attached without asking storage about
    every file. Attachments recorded before this was tracked read as ``0`` — they were
    accepted under a per-file rule, and counting them as nothing is the reading that
    cannot retroactively invalidate a submission.
    """

    _id: AttachmentId
    _type: AttachmentType
    _file: FileReference
    _caption: str | None = None
    _size_bytes: int = 0

    @classmethod
    def create(
        cls,
        *,
        attachment_id: AttachmentId,
        attachment_type: AttachmentType,
        file: FileReference,
        caption: str | None = None,
        size_bytes: int = 0,
    ) -> Attachment:
        return cls(
            _id=attachment_id,
            _type=attachment_type,
            _file=file,
            _caption=cls._clean_caption(caption),
            _size_bytes=max(0, size_bytes),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        attachment_id: AttachmentId,
        attachment_type: AttachmentType,
        file: FileReference,
        caption: str | None = None,
        size_bytes: int = 0,
    ) -> Attachment:
        return cls(_id=attachment_id, _type=attachment_type, _file=file, _caption=caption, _size_bytes=max(0, size_bytes))

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

    @property
    def size_bytes(self) -> int:
        """The file's size, or ``0`` for attachments recorded before it was tracked."""
        return self._size_bytes

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
    _status_history: list[SubmissionStatusChange] = field(default_factory=list)
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
            _status_history=[SubmissionStatusChange(from_status=None, to_status=SubmissionStatus.DRAFT, occurred_at=now)],
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
        status_history: Sequence[SubmissionStatusChange] = (),
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
            _status_history=list(status_history),
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
    def status_history(self) -> tuple[SubmissionStatusChange, ...]:
        """The submission's status history, in the order it was recorded."""
        return tuple(self._status_history)

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
        """Whether content may currently be changed (DRAFT, SUBMITTED or REQUIRES_CORRECTION)."""
        return self._status in _EDITABLE_STATUSES

    def is_correctable_by_organizer(self) -> bool:
        """Whether the organizer may still correct the content — the whole live lifecycle.

        Wider than :meth:`is_editable` for the reason spelled out in
        :meth:`_ensure_editable`: the organizer owns what the entry says, and most
        mistakes are noticed after the applicant's own window has closed.
        """
        return self._status in _LIVE_STATUSES

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def set_performance(self, *, performance: Performance, now: datetime, by_organizer: bool = False) -> list[DomainEvent]:
        """Set or replace the submission's single performance (editable states only).

        ``by_organizer`` widens the window to the whole live lifecycle — see
        :meth:`_ensure_editable`.
        """
        self._ensure_editable(by_organizer=by_organizer)
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
        members: Sequence[str] = (),
        now: datetime,
        by_organizer: bool = False,
    ) -> list[DomainEvent]:
        """Add a participant (a Participant Registry snapshot: solo or collective).

        ``member_count`` is the headcount this entry represents: 1 for a solo person,
        the number of people for a collective/ensemble - it drives the participant-count
        band check and per-participant pricing. ``members`` optionally names those
        people, which is how the applicant asks for an individual diploma each (see
        :meth:`set_participant_members`). Rejects a future birth date and a duplicate
        (the same registry participant, or - for manual entries - the same display name
        and birth date, already on this submission).

        ``by_organizer`` widens the window to the whole live lifecycle — see
        :meth:`_ensure_editable`.
        """
        self._ensure_editable(by_organizer=by_organizer)
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
            members=members,
        )
        if any(p.identity_key == candidate.identity_key for p in self._participants.values()):
            raise DuplicateParticipantError(f"Участник «{candidate.display_name}» уже добавлен в выступление.")
        self._participants[participant_id] = candidate
        self._touch(now)
        return [ParticipantAdded(aggregate_id=self._id.value, participant_id=participant_id)]

    def set_participant_members(
        self, *, participant_id: ParticipantId, members: Sequence[str], now: datetime, by_organizer: bool = False
    ) -> list[DomainEvent]:
        """Name the people in a collective - the applicant's request for individual documents.

        Optional by design: an applicant who wants only the collective's own diploma
        leaves the roster empty, and an applicant who wants a diploma per person fills
        it in. Sending an empty list withdraws the request, which is why this replaces
        the whole roster rather than appending to it.

        Editable states only, like every other content change: past ``ACCEPTED`` the
        entry is what the organizer accepted, and the names on it are part of that —
        which is also why ``by_organizer`` lifts the freeze: it is their own record.
        """
        self._ensure_editable(by_organizer=by_organizer)
        participant = self._participants.get(participant_id)
        if participant is None:
            raise ParticipantNotFoundError(f"No participant {participant_id} in this submission.")
        participant.with_members(members)
        self._touch(now)
        return [ParticipantMembersChanged(aggregate_id=self._id.value, participant_id=participant_id)]

    def set_participant_member_count(
        self, *, participant_id: ParticipantId, member_count: int, now: datetime, by_organizer: bool = False
    ) -> list[DomainEvent]:
        """Correct how many people a collective entry stands for.

        The headcount arrives with the entry, but it is the one thing about a
        collective the applicant is likely to get wrong first time - it drives the
        count-band check and per-participant pricing, both of which they only see
        afterwards. Fixing it must not cost them the roster they already typed, so
        this changes the entry rather than replacing it.
        """
        self._ensure_editable(by_organizer=by_organizer)
        participant = self._participants.get(participant_id)
        if participant is None:
            raise ParticipantNotFoundError(f"No participant {participant_id} in this submission.")
        participant.with_member_count(member_count)
        self._touch(now)
        return [ParticipantMemberCountChanged(aggregate_id=self._id.value, participant_id=participant_id)]

    def remove_participant(self, *, participant_id: ParticipantId, now: datetime, by_organizer: bool = False) -> list[DomainEvent]:
        """Remove a participant.

        A DRAFT (or REQUIRES_CORRECTION) submission may be left temporarily without
        participants so the applicant can freely swap the sole one; the "at least one
        participant" invariant is enforced when the submission is submitted, not while
        it is being edited.
        """
        self._ensure_editable(by_organizer=by_organizer)
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
        by_organizer: bool = False,
    ) -> list[DomainEvent]:
        """Credit a teacher in a configurable role.

        ``directory_teacher_id`` links a teacher chosen from the reusable Teacher
        Directory; ``name``/``role`` are the immutable snapshot preserved on the
        submission so later directory edits never rewrite it.
        """
        self._ensure_editable(by_organizer=by_organizer)
        teacher = Teacher.create(teacher_id=teacher_id, name=name, role=role, directory_teacher_id=directory_teacher_id)
        self._teachers[teacher_id] = teacher
        self._touch(now)
        return [TeacherAdded(aggregate_id=self._id.value, teacher_id=teacher_id, role=role)]

    def remove_teacher(self, *, teacher_id: TeacherId, now: datetime, by_organizer: bool = False) -> list[DomainEvent]:
        """Remove a teacher."""
        self._ensure_editable(by_organizer=by_organizer)
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
        size_bytes: int = 0,
    ) -> list[DomainEvent]:
        """Add an attachment reference. Rejects duplicates (the same file referenced twice).

        A submission may carry **several** attachments of the same kind: an act can be
        performed to more than one phonogram (a backing track and a fanfare, a two-part
        number), and photographs come in handfuls. The only thing refused is the same file
        twice.
        """
        self._ensure_attachable(attachment_type)
        if any(a.file == file for a in self._attachments.values()):
            raise DuplicateAttachmentError(f"An attachment referencing {file.value!r} is already in this submission.")
        attachment = Attachment.create(
            attachment_id=attachment_id,
            attachment_type=attachment_type,
            file=file,
            caption=caption,
            size_bytes=size_bytes,
        )
        self._attachments[attachment_id] = attachment
        self._touch(now)
        return [AttachmentAdded(aggregate_id=self._id.value, attachment_id=attachment_id, attachment_type=attachment_type)]

    def attached_bytes(self, kinds: Collection[str]) -> int:
        """Total size of the attachments whose kind is in ``kinds``.

        What a shared ceiling is measured against. Sizes recorded as ``0`` (attachments
        from before they were tracked) simply do not add to it, which under-counts rather
        than retroactively pushing an existing submission over its limit.
        """
        return sum(a.size_bytes for a in self._attachments.values() if a.type.value in kinds)

    def remove_attachment(self, *, attachment_id: AttachmentId, now: datetime) -> list[DomainEvent]:
        """Remove an attachment reference.

        Removable exactly as long as its kind was attachable: a track that can still be
        added can still be replaced, which is what "заменить фонограмму" is.
        """
        attachment = self._attachments.get(attachment_id)
        self._ensure_attachable(attachment.type if attachment is not None else None)
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
        participant exists, an immutable price snapshot exists **when the competition
        priced the combination** (``policy.is_priced``), the ages are stated when the
        chosen age category is a mixed one (``policy.requires_age_composition``), the
        performance's combination is admissible, and the participant count matches the
        configured participant group's band (validated against the supplied read-model
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

        From here content is permanently frozen and the applicant can no longer
        withdraw - the submission is committed to the running order. Only the
        organizer may still take it out (:meth:`cancel_by_organizer`).
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
        """Withdraw the submission at the applicant's request.

        Refused once the submission is committed to the running order: from there a
        withdrawal is the organizer's decision, not the applicant's — see
        :meth:`cancel_by_organizer`.
        """
        if self._status in _ORGANIZER_ONLY_CANCELLABLE_STATUSES:
            raise IllegalStatusTransitionError(f"A submission that is {self._status.value} can only be cancelled by the organizer.")
        return self._cancel(now=now)

    def cancel_by_organizer(self, *, now: datetime) -> list[DomainEvent]:
        """Cancel the submission by organizer decision (withdrawal or rejection).

        Reaches further than :meth:`cancel`: an entry already committed to the running
        order may still be taken out of it, case by case. ``COMPLETED`` remains
        terminal — a performance that happened cannot be un-entered.
        """
        return self._cancel(now=now)

    def _cancel(self, *, now: datetime) -> list[DomainEvent]:
        """Perform the cancellation itself, once the caller's authority is settled."""
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
            raise PerformanceRequiredError("Заполните выступление: жанр, название и длительность номера.")
        if not self._participants:
            raise ParticipantRequiredError("Добавьте хотя бы одного участника.")
        if policy.is_priced and self._price_snapshot is None:
            raise PriceSnapshotRequiredError("Не рассчитана стоимость участия — обновите страницу и попробуйте ещё раз.")
        if not policy.is_admissible:
            raise CombinationNotAdmissibleError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
        if not policy.allows_participant_count(self.participant_count):
            raise ParticipantCountMismatchError(
                f"Число участников ({self.participant_count}) не подходит под выбранный состав: нужно {policy.participant_count_range}."
            )
        if policy.requires_age_composition and not self._performance.age_composition:
            raise AgeCompositionRequiredError("Категория смешанная: укажите, участники какого возраста выходят на сцену.")
        if policy.requires_teacher and not self._teachers:
            raise TeacherRequiredError("Этот фестиваль требует указать педагога.")
        if not policy.allows_participant_comment and self._performance.comment:
            raise ParticipantCommentNotAcceptedError("Этот фестиваль не принимает комментарий к выступлению — очистите поле комментария.")
        present_types = {attachment.type for attachment in self._attachments.values()}
        missing = policy.required_attachment_types() - present_types
        if missing:
            kinds = ", ".join(sorted(_ATTACHMENT_LABELS_RU[kind] for kind in missing))
            raise RequiredAttachmentMissingError(f"Перед подачей нужно приложить: {kinds}.")

    def _ensure_editable(self, *, by_organizer: bool = False) -> None:
        """Whether the content may be changed right now, by this kind of caller.

        The applicant's reach is :data:`_EDITABLE_STATUSES` — past that the entry is
        what the organizer reviewed, and letting the applicant rewrite it afterwards
        would make the review meaningless.

        The organizer's reach is the whole live lifecycle. They are the one who
        decides what the entry says, and by the time a mistake is noticed the entry is
        usually already past the freeze: approval takes it straight into the running
        order, so "вернуть участнику на исправление" is the only remaining repair and
        it costs a round trip for a misspelt surname that will be printed on a diploma.
        Correcting it in place is the same decision, made directly. ``COMPLETED`` and
        ``CANCELLED`` stay closed to everyone: the performance happened, or there will
        not be one, and neither is a fact a correction can change.
        """
        if by_organizer:
            if self._status not in _LIVE_STATUSES:
                raise SubmissionNotEditableError("Заявка завершена или отменена — изменить её нельзя.")
            return
        if self._status not in _EDITABLE_STATUSES:
            raise SubmissionNotEditableError("Выступление уже рассмотрено организатором — изменить его нельзя.")

    def _ensure_attachable(self, attachment_type: AttachmentType | None) -> None:
        """Whether a file of this kind may be attached or detached right now.

        Most kinds are content and follow the content freeze. The kinds in
        :data:`_LATE_ATTACHMENT_TYPES` follow the entry instead: they may come and go
        for as long as the entry is live, because they are needed *after* it has been
        accepted. ``None`` (an attachment id that matches nothing) takes the strict
        path — the caller is about to be told it does not exist anyway.
        """
        if attachment_type is None or attachment_type not in _LATE_ATTACHMENT_TYPES:
            self._ensure_editable()
            return
        if self._status not in _LIVE_STATUSES:
            raise SubmissionNotEditableError(f"Файл «{_ATTACHMENT_LABELS_RU[attachment_type]}» можно приложить, только пока заявка в работе.")

    def _transition_to(self, target: SubmissionStatus, *, now: datetime) -> None:
        """Move to ``target`` if the transition is legal from the current status."""
        if target not in _LEGAL_TRANSITIONS[self._status]:
            raise IllegalStatusTransitionError(f"Cannot transition from {self._status.value} to {target.value}.")
        previous = self._status
        self._status = target
        self._status_history.append(SubmissionStatusChange(from_status=previous, to_status=target, occurred_at=now))
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
_APPLICATION_EDITABLE_STATUSES: Final = frozenset({ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED})

#: Statuses in which the applicant may attach or detach payment receipts:
#: any time before the order is settled. Some festivals require payment upfront, so
#: a receipt may be uploaded while the order is still a DRAFT in the wizard, through
#: submission and while awaiting payment; a paid/completed/cancelled order is settled.
_APPLICATION_RECEIPT_STATUSES: Final = frozenset({ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, ApplicationStatus.WAITING_PAYMENT})

#: How many payment receipts one order may carry. Paying the total in several
#: transfers is ordinary; twenty slips for one order is a stuck client, not an
#: applicant, and the cap keeps the JSON column (and the organizer's folder) sane.
_MAX_PAYMENT_RECEIPTS: Final = 20

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
    #: Who the festival's contract is signed with, and so who the payment for this
    #: order comes from. A plain natural person: for a collective the leader, for an
    #: adult entrant themselves, for a child their legal representative. Absent
    #: unless the competition asks for it (``collect_payer_details``).
    _payer_name: PersonName | None = None
    _submission_refs: dict[SubmissionId, SubmissionRef] = field(default_factory=dict)
    _service_lines: dict[ServiceId, ServiceLine] = field(default_factory=dict)
    _consents: tuple[Consent, ...] = ()
    _total_price: TotalPriceSnapshot | None = None
    _status_history: list[ApplicationStatusChange] = field(default_factory=list)
    _payment_receipts: list[PaymentReceipt] = field(default_factory=list)
    _paid_at: datetime | None = None
    _submitted_at: datetime | None = None
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
        payer_name: PersonName | None = None,
        submission_refs: Sequence[SubmissionRef] = (),
        service_lines: Sequence[ServiceLine] = (),
        consents: Sequence[Consent] = (),
        total_price: TotalPriceSnapshot | None = None,
        status_history: Sequence[ApplicationStatusChange] = (),
        payment_receipts: Sequence[PaymentReceipt] = (),
        paid_at: datetime | None = None,
        submitted_at: datetime | None = None,
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
            _payer_name=payer_name,
            _submission_refs={ref.submission_id: ref for ref in submission_refs},
            _service_lines={line.service_id: line for line in service_lines},
            _consents=tuple(consents),
            _total_price=total_price,
            _status_history=list(status_history),
            _payment_receipts=list(payment_receipts),
            _paid_at=paid_at,
            _submitted_at=submitted_at,
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
    def payer_name(self) -> PersonName | None:
        """The person the contract is signed with, if the festival collects one."""
        return self._payer_name

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
    def payment_receipts(self) -> tuple[PaymentReceipt, ...]:
        """Every proof of payment attached to the order, oldest upload first."""
        return tuple(self._payment_receipts)

    @property
    def has_payment_receipt(self) -> bool:
        """Whether any proof of payment is attached at all.

        The question the order lifecycle actually asks — the auto-cancel sweep and
        the submission confirmation care that *something* was paid, not how many
        transfers it took.
        """
        return bool(self._payment_receipts)

    @property
    def paid_at(self) -> datetime | None:
        return self._paid_at

    @property
    def submitted_at(self) -> datetime | None:
        """When the order was submitted (drives the unpaid auto-cancel deadline)."""
        return self._submitted_at

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
        """Whether payment receipts may currently be attached or detached (before settled)."""
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

    def set_payer(self, *, name: PersonName, now: datetime) -> list[DomainEvent]:
        """Name (or rename) the person the festival's contract is signed with.

        Editable for exactly as long as the rest of the order's composition is
        (``DRAFT``/``SUBMITTED``): a misspelt surname on a submitted order is corrected
        the same way a wrong service line is, and once the order is billed the
        documents are already drawn up. Calling it again replaces the name rather than
        adding a second payer — one order, one contract, one party.
        """
        self._ensure_editable()
        self._payer_name = name
        self._touch(now)
        return [PayerRecorded(aggregate_id=self._id.value, payer_full_name=name.full_name)]

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
        cached status/price/display, and recomputes the order total while the order
        is still editable (DRAFT/SUBMITTED). Refreshes past payment are ignored.
        """
        if self._status not in _APPLICATION_REFRESHABLE_STATUSES:
            return []
        if ref.submission_id not in self._submission_refs:
            raise SubmissionRefNotFoundError(f"Submission {ref.submission_id.json()} is not attached to this application.")
        self._submission_refs[ref.submission_id] = ref
        if self._status in _APPLICATION_EDITABLE_STATUSES:
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
        payer_required: bool = False,
        now: datetime,
    ) -> list[DomainEvent]:
        """Submit the order (DRAFT -> SUBMITTED), freezing its total price.

        Enforces the order invariants: at least one submission is attached, every
        consent the competition requires has been recorded, every additional service
        the competition mandates has been selected, and - where the festival draws up
        documents per order - a payer has been named. The total price is recomputed
        once and then frozen - future Competition pricing changes can never alter an
        order already placed. Submitting the individual Submissions for review is an
        application-layer concern (orchestrated over their own aggregate); this
        transition governs only the order.

        ``payer_required`` is passed in rather than read here for the same reason the
        consent codes are: whether this festival signs a contract per application is
        the Competition's configuration, and this aggregate validates against a
        projection of it instead of importing it.
        """
        if not self._submission_refs:
            raise NoSubmissionsError("В заявке нет ни одного выступления.")
        if payer_required and self._payer_name is None:
            raise PayerRequiredError("Укажите заказчика: фестиваль оформляет документы по заявке.")
        recorded = {consent.code for consent in self._consents}
        missing_consents = required_consent_codes - recorded
        if missing_consents:
            raise MissingRequiredConsentError("Подтвердите обязательные согласия — без них заявку подать нельзя.")
        selected_services = {line.service_id.json() for line in self._service_lines.values()}
        missing_services = required_service_ids - selected_services
        if missing_services:
            raise MissingRequiredServiceError("Выберите обязательные дополнительные услуги фестиваля.")
        total = self._recalculate_total(now)
        self._transition_to(ApplicationStatus.SUBMITTED, now=now)
        self._submitted_at = now
        return [ApplicationSubmitted(aggregate_id=self._id.value, amount=str(total.amount), currency=total.currency)]

    def request_payment(self, *, now: datetime) -> list[DomainEvent]:
        """Move the order to awaiting payment (SUBMITTED -> WAITING_PAYMENT).

        The derived readiness gate: allowed only once **every** referenced
        submission is approved. Readiness is read from the cached submission
        statuses (kept fresh by the projection); the Application never runs its own
        review.
        """
        if not self.is_ready_for_payment():
            raise NotAllSubmissionsApprovedError("Оплата станет доступна, когда организатор одобрит все выступления заявки.")
        self._transition_to(ApplicationStatus.WAITING_PAYMENT, now=now)
        return [ApplicationAwaitingPayment(aggregate_id=self._id.value)]

    def upload_payment_receipt(self, *, file: FileReference, now: datetime) -> list[DomainEvent]:
        """Attach one more proof of payment to the order.

        Allowed any time before the order is settled (``DRAFT``, ``SUBMITTED`` or
        ``WAITING_PAYMENT``) - festivals that require upfront payment let the applicant
        attach a receipt while still filling in the draft; a paid/closed order is
        final. This does not change the order status; the organizer still confirms
        payment separately.

        Uploading **adds** rather than replaces: the total is regularly settled by
        several transfers, and a second slip is normally the rest of the payment, not
        a correction of the first. A receipt uploaded by mistake is taken back with
        :meth:`remove_payment_receipt`.
        """
        if self._status not in _APPLICATION_RECEIPT_STATUSES:
            raise PaymentReceiptNotAllowedError(f"A payment receipt cannot be attached once the application is settled ({self._status.value}).")
        if len(self._payment_receipts) >= _MAX_PAYMENT_RECEIPTS:
            raise TooManyPaymentReceiptsError(
                f"The application already carries {len(self._payment_receipts)} payment receipts (the maximum is {_MAX_PAYMENT_RECEIPTS})."
            )
        receipt = PaymentReceipt(id=PaymentReceiptId.generate(), file=file, uploaded_at=now)
        self._payment_receipts.append(receipt)
        self._touch(now)
        return [PaymentReceiptUploaded(aggregate_id=self._id.value, receipt_id=receipt.id)]

    def remove_payment_receipt(self, *, receipt_id: PaymentReceiptId, now: datetime) -> list[DomainEvent]:
        """Detach one of the order's payment receipts (the wrong file, or a duplicate).

        Same window as attaching one: while the order is still unsettled. Removing a
        receipt that is not on the order is an error rather than a silent no-op — the
        applicant asked to take back a specific file, and pretending it worked would
        leave the wrong slip in the organizer's folder.
        """
        if self._status not in _APPLICATION_RECEIPT_STATUSES:
            raise PaymentReceiptNotAllowedError(f"A payment receipt cannot be removed once the application is settled ({self._status.value}).")
        remaining = [receipt for receipt in self._payment_receipts if receipt.id != receipt_id]
        if len(remaining) == len(self._payment_receipts):
            raise PaymentReceiptNotFoundError(f"No payment receipt {receipt_id.json()} on this application.")
        self._payment_receipts = remaining
        self._touch(now)
        return [PaymentReceiptRemoved(aggregate_id=self._id.value, receipt_id=receipt_id)]

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
            raise ApplicationNotEditableError(
                f"An application's composition can only be changed while DRAFT or SUBMITTED, not while {self._status.value}."
            )

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
