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
from typing import Final

from .events import (
    AttachmentAdded,
    AttachmentRemoved,
    DomainEvent,
    ParticipantAdded,
    ParticipantRemoved,
    PerformanceDefined,
    PriceSnapshotCreated,
    ReviewAdded,
    SubmissionAccepted,
    SubmissionApproved,
    SubmissionAwaitingPayment,
    SubmissionCancelled,
    SubmissionCompleted,
    SubmissionCreated,
    SubmissionPaid,
    SubmissionReturnedForCorrection,
    SubmissionReviewStarted,
    SubmissionScheduled,
    SubmissionSubmitted,
    TeacherAdded,
    TeacherRemoved,
)
from .exceptions import (
    AttachmentNotFoundError,
    CannotRemoveLastParticipantError,
    CombinationNotAdmissibleError,
    DirectConstructionError,
    DuplicateAttachmentError,
    DuplicateParticipantError,
    IllegalStatusTransitionError,
    InvalidBirthDateError,
    ParticipantCountMismatchError,
    ParticipantNotFoundError,
    ParticipantRequiredError,
    PerformanceRequiredError,
    PriceSnapshotLockedError,
    PriceSnapshotRequiredError,
    SubmissionNotEditableError,
    TeacherNotFoundError,
)
from .value_objects import (
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    FileReference,
    Gender,
    ParticipantId,
    Performance,
    PersonName,
    PriceSnapshot,
    ReviewComment,
    ReviewerId,
    ReviewId,
    SubmissionId,
    SubmissionParticipationPolicy,
    SubmissionStatus,
    TeacherId,
    TeacherRole,
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
    """A person taking part in the performance.

    **Documented extension points (deliberately NOT implemented):** citizenship,
    identity document, disability, achievements. Each would land as a new optional
    value object on this entity without changing the aggregate shape.
    """

    _id: ParticipantId
    _name: PersonName
    _birth_date: BirthDate
    _gender: Gender

    @classmethod
    def create(cls, *, participant_id: ParticipantId, name: PersonName, birth_date: BirthDate, gender: Gender) -> Participant:
        return cls(_id=participant_id, _name=name, _birth_date=birth_date, _gender=gender)

    @classmethod
    def rehydrate(cls, *, participant_id: ParticipantId, name: PersonName, birth_date: BirthDate, gender: Gender) -> Participant:
        return cls(_id=participant_id, _name=name, _birth_date=birth_date, _gender=gender)

    @property
    def id(self) -> ParticipantId:
        return self._id

    @property
    def name(self) -> PersonName:
        return self._name

    @property
    def birth_date(self) -> BirthDate:
        return self._birth_date

    @property
    def gender(self) -> Gender:
        return self._gender

    @property
    def identity_key(self) -> tuple[PersonName, BirthDate]:
        """The natural key used to detect duplicate participants (name + birth date)."""
        return (self._name, self._birth_date)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Participant) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Participant(id={self._id!r}, name={self._name.full_name!r})"


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

    @classmethod
    def create(cls, *, teacher_id: TeacherId, name: PersonName, role: TeacherRole) -> Teacher:
        return cls(_id=teacher_id, _name=name, _role=role)

    @classmethod
    def rehydrate(cls, *, teacher_id: TeacherId, name: PersonName, role: TeacherRole) -> Teacher:
        return cls(_id=teacher_id, _name=name, _role=role)

    @property
    def id(self) -> TeacherId:
        return self._id

    @property
    def name(self) -> PersonName:
        return self._name

    @property
    def role(self) -> TeacherRole:
        return self._role

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
        return len(self._participants)

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
        name: PersonName,
        birth_date: BirthDate,
        gender: Gender,
        now: datetime,
    ) -> list[DomainEvent]:
        """Add a participant. Rejects duplicates (same name + birth date) and future birth dates."""
        self._ensure_editable()
        if birth_date.value > now.date():
            raise InvalidBirthDateError(f"Birth date {birth_date} must not be in the future.")
        key = (name, birth_date)
        if any(p.identity_key == key for p in self._participants.values()):
            raise DuplicateParticipantError(f"Participant {name.full_name!r} ({birth_date}) is already in this submission.")
        participant = Participant.create(participant_id=participant_id, name=name, birth_date=birth_date, gender=gender)
        self._participants[participant_id] = participant
        self._touch(now)
        return [ParticipantAdded(aggregate_id=self._id.value, participant_id=participant_id)]

    def remove_participant(self, *, participant_id: ParticipantId, now: datetime) -> list[DomainEvent]:
        """Remove a participant. The last remaining participant cannot be removed."""
        self._ensure_editable()
        if participant_id not in self._participants:
            raise ParticipantNotFoundError(f"No participant {participant_id} in this submission.")
        if len(self._participants) == 1:
            raise CannotRemoveLastParticipantError("Cannot remove the only remaining participant; add another first.")
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
        now: datetime,
    ) -> list[DomainEvent]:
        """Add a teacher in a configurable role."""
        self._ensure_editable()
        teacher = Teacher.create(teacher_id=teacher_id, name=name, role=role)
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
        if not policy.allows_participant_count(len(self._participants)):
            raise ParticipantCountMismatchError(
                f"Participant count {len(self._participants)} does not match the configured group range {policy.participant_count_range}."
            )

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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Submission) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Submission(id={self._id!r}, status={self._status.value!r}, participants={len(self._participants)})"


__all__ = [
    "Attachment",
    "Participant",
    "Review",
    "Submission",
    "Teacher",
]
