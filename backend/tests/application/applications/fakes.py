"""In-memory fakes for the Applications application ports.

Framework-free, database-free test doubles that structurally satisfy the ports in
:mod:`apps.applications.application.interfaces`. Not a test module (no ``test_``
prefix), so pytest does not collect it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.applications.application.interfaces import ApplicantInfo
from apps.applications.domain.entities import Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    CompetitionId,
    Money,
    ParticipantCountRange,
    ReviewerId,
    SubmissionId,
    SubmissionParticipationPolicy,
    UserId,
    _generate_uuid7,
)

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def uuid7_str() -> str:
    """A fresh UUID v7 rendered as a canonical string (for command payloads)."""
    return str(_generate_uuid7())


class FakeClock:
    def now(self) -> datetime:
        return NOW

    def utcnow(self) -> datetime:
        return NOW


class SequenceUuidGenerator:
    """Deterministic UUID v7 source (each call returns a fresh, distinct id)."""

    def new(self) -> uuid.UUID:
        return _generate_uuid7()


class RecordingEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)


class FakeSubmissionRepository:
    def __init__(self) -> None:
        self._by_id: dict[SubmissionId, Submission] = {}
        self.saved: list[Submission] = []
        self.deleted: list[SubmissionId] = []

    def get(self, submission_id: SubmissionId) -> Submission | None:
        return self._by_id.get(submission_id)

    def exists(self, submission_id: SubmissionId) -> bool:
        return submission_id in self._by_id

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Submission]:
        return [s for s in self._by_id.values() if s.applicant_id == applicant_id and not s.is_deleted]

    def list_by_competition(self, competition_id: CompetitionId) -> Sequence[Submission]:
        return [s for s in self._by_id.values() if s.competition_id == competition_id and not s.is_deleted]

    def save(self, submission: Submission) -> None:
        self._by_id[submission.id] = submission
        self.saved.append(submission)

    def delete(self, submission_id: SubmissionId) -> None:
        self._by_id.pop(submission_id, None)
        self.deleted.append(submission_id)


class FakeCompetitionCatalog:
    """Configurable Competition ACL stand-in (admissible & priced by default)."""

    def __init__(
        self,
        *,
        known: bool = True,
        open_for_submissions: bool = True,
        policy: SubmissionParticipationPolicy | None = None,
        price: Money | None = None,
    ) -> None:
        self.known = known
        self.open_for_submissions = open_for_submissions
        self.policy: SubmissionParticipationPolicy | None = (
            policy
            if policy is not None
            else SubmissionParticipationPolicy(
                participant_count_range=ParticipantCountRange(min_count=1),
                is_admissible=True,
            )
        )
        self.price: Money | None = price if price is not None else Money.of("500.00")

    def exists(self, competition_id: CompetitionId) -> bool:
        return self.known

    def accepts_submissions(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        return self.open_for_submissions

    def participation_policy(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: object,
        discipline_id: object,
        age_category_id: object,
        participant_group_id: object,
        participation_format_id: object,
    ) -> SubmissionParticipationPolicy | None:
        return self.policy

    def price_per_participant(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: object,
        discipline_id: object,
        age_category_id: object,
        participant_group_id: object,
        participation_format_id: object,
    ) -> Money | None:
        return self.price


class FakeOrganizationReadModel:
    """Organization ACL stand-in; every reviewer is authorized unless set otherwise."""

    def __init__(self, *, staff: bool = True, reviewer: bool = True) -> None:
        self._staff = staff
        self._reviewer = reviewer

    def has_staff_permission(self, *, user_id: UserId) -> bool:
        return self._staff

    def can_review_submissions(self, *, reviewer_id: ReviewerId) -> bool:
        return self._reviewer


class FakeIdentityReadModel:
    """Identity ACL stand-in; the applicant exists unless set otherwise."""

    def __init__(self, *, known: bool = True) -> None:
        self._known = known

    def exists(self, *, user_id: UserId) -> bool:
        return self._known

    def get_applicant(self, *, user_id: UserId) -> ApplicantInfo | None:
        if not self._known:
            return None
        return ApplicantInfo(user_id=user_id.json(), display_name="Test Applicant", email="applicant@example.com")
