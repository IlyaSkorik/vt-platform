"""Result & view DTOs for the Applications application layer.

Immutable, primitive-only output shapes. They are the boundary in the *outward*
direction: handlers render the :class:`Submission` aggregate (and its child
entities and value objects) into flat, serialization-agnostic DTOs so no outer
layer needs to import the domain to read a result. Ids and enums are rendered as
strings, money as a decimal string, and temporal values as ``datetime`` / ``date``.

Command handlers return a :class:`SubmissionOperationResultDto` (the updated view
plus the events produced); query handlers return the read views directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from apps.applications.domain.entities import (
    Attachment,
    Participant,
    Review,
    Submission,
    Teacher,
)
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import Performance, PriceSnapshot

__all__ = [
    "AttachmentView",
    "ParticipantView",
    "PerformanceView",
    "PriceView",
    "ReviewView",
    "SubmissionHistoryDto",
    "SubmissionOperationResultDto",
    "SubmissionSummaryView",
    "SubmissionView",
    "TeacherView",
]


@dataclass(frozen=True, slots=True)
class PerformanceView:
    """A flat read view of a submission's single :class:`Performance`."""

    title: str
    duration_seconds: int
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str

    @classmethod
    def from_performance(cls, performance: Performance) -> PerformanceView:
        """Project a :class:`Performance` value object into its read view."""
        return cls(
            title=performance.title.value,
            duration_seconds=performance.duration.seconds,
            nomination_id=performance.nomination_id.json(),
            discipline_id=performance.discipline_id.json(),
            age_category_id=performance.age_category_id.json(),
            participant_group_id=performance.participant_group_id.json(),
            participation_format_id=performance.participation_format_id.json(),
        )


@dataclass(frozen=True, slots=True)
class ParticipantView:
    """A flat read view of a :class:`Participant` child entity.

    Registry-linked participants carry ``registry_participant_id``; a collective has
    only a ``display_name`` (its structured name/birth-date/gender are ``None``).
    """

    id: str
    display_name: str
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    birth_date: date | None
    gender: str | None
    registry_participant_id: str | None

    @classmethod
    def from_participant(cls, participant: Participant) -> ParticipantView:
        """Project a :class:`Participant` into its read view."""
        name = participant.name
        birth_date = participant.birth_date
        gender = participant.gender
        registry_id = participant.registry_participant_id
        return cls(
            id=participant.id.json(),
            display_name=participant.display_name,
            first_name=name.first_name if name is not None else None,
            last_name=name.last_name if name is not None else None,
            middle_name=name.middle_name if name is not None else None,
            birth_date=birth_date.value if birth_date is not None else None,
            gender=gender.value if gender is not None else None,
            registry_participant_id=registry_id.json() if registry_id is not None else None,
        )


@dataclass(frozen=True, slots=True)
class TeacherView:
    """A flat read view of a :class:`Teacher` child entity."""

    id: str
    first_name: str
    last_name: str
    middle_name: str | None
    role: str
    directory_teacher_id: str | None

    @classmethod
    def from_teacher(cls, teacher: Teacher) -> TeacherView:
        """Project a :class:`Teacher` into its read view."""
        directory_id = teacher.directory_teacher_id
        return cls(
            id=teacher.id.json(),
            first_name=teacher.name.first_name,
            last_name=teacher.name.last_name,
            middle_name=teacher.name.middle_name,
            role=teacher.role.value,
            directory_teacher_id=directory_id.json() if directory_id is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AttachmentView:
    """A flat read view of an :class:`Attachment` child entity."""

    id: str
    type: str
    file_reference: str
    caption: str | None

    @classmethod
    def from_attachment(cls, attachment: Attachment) -> AttachmentView:
        """Project an :class:`Attachment` into its read view."""
        return cls(
            id=attachment.id.json(),
            type=attachment.type.value,
            file_reference=attachment.file.value,
            caption=attachment.caption,
        )


@dataclass(frozen=True, slots=True)
class ReviewView:
    """A flat read view of a :class:`Review` iteration."""

    id: str
    reviewer_id: str
    comment: str
    created_at: datetime

    @classmethod
    def from_review(cls, review: Review) -> ReviewView:
        """Project a :class:`Review` into its read view."""
        return cls(
            id=review.id.json(),
            reviewer_id=review.reviewer_id.json(),
            comment=review.comment.value,
            created_at=review.created_at,
        )


@dataclass(frozen=True, slots=True)
class PriceView:
    """A flat read view of a submission's immutable :class:`PriceSnapshot`."""

    amount: str
    currency: str
    calculated_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: PriceSnapshot) -> PriceView:
        """Project a :class:`PriceSnapshot` into its read view."""
        return cls(
            amount=str(snapshot.amount),
            currency=snapshot.currency.value,
            calculated_at=snapshot.calculated_at,
        )


@dataclass(frozen=True, slots=True)
class SubmissionView:
    """The full read view of a :class:`Submission` aggregate (root + children)."""

    id: str
    competition_id: str
    applicant_id: str
    status: str
    performance: PerformanceView | None
    participants: tuple[ParticipantView, ...]
    teachers: tuple[TeacherView, ...]
    attachments: tuple[AttachmentView, ...]
    reviews: tuple[ReviewView, ...]
    price: PriceView | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_submission(cls, submission: Submission) -> SubmissionView:
        """Project the whole :class:`Submission` aggregate into a flat detail view."""
        performance = submission.performance
        price = submission.price_snapshot
        return cls(
            id=submission.id.json(),
            competition_id=submission.competition_id.json(),
            applicant_id=submission.applicant_id.json(),
            status=submission.status.value,
            performance=PerformanceView.from_performance(performance) if performance is not None else None,
            participants=tuple(ParticipantView.from_participant(p) for p in submission.participants),
            teachers=tuple(TeacherView.from_teacher(t) for t in submission.teachers),
            attachments=tuple(AttachmentView.from_attachment(a) for a in submission.attachments),
            reviews=tuple(ReviewView.from_review(r) for r in submission.reviews),
            price=PriceView.from_snapshot(price) if price is not None else None,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            version=submission.version,
        )


@dataclass(frozen=True, slots=True)
class SubmissionSummaryView:
    """A lightweight read view of a submission for list endpoints (no child graph)."""

    id: str
    competition_id: str
    applicant_id: str
    status: str
    participant_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_submission(cls, submission: Submission) -> SubmissionSummaryView:
        """Project a :class:`Submission` into its lightweight summary view."""
        return cls(
            id=submission.id.json(),
            competition_id=submission.competition_id.json(),
            applicant_id=submission.applicant_id.json(),
            status=submission.status.value,
            participant_count=submission.participant_count,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
        )


@dataclass(frozen=True, slots=True)
class SubmissionHistoryDto:
    """A submission's review history plus its current status."""

    submission_id: str
    current_status: str
    reviews: tuple[ReviewView, ...]

    @classmethod
    def from_submission(cls, submission: Submission) -> SubmissionHistoryDto:
        """Project a :class:`Submission` into its review-history view."""
        return cls(
            submission_id=submission.id.json(),
            current_status=submission.status.value,
            reviews=tuple(ReviewView.from_review(r) for r in submission.reviews),
        )


@dataclass(frozen=True, slots=True)
class SubmissionOperationResultDto:
    """The outcome of a command: the updated submission view plus the events produced."""

    submission: SubmissionView
    events: tuple[DomainEvent, ...]

    @classmethod
    def of(cls, submission: Submission, events: tuple[DomainEvent, ...]) -> SubmissionOperationResultDto:
        """Build a result DTO from the mutated aggregate and its new events."""
        return cls(submission=SubmissionView.from_submission(submission), events=events)
