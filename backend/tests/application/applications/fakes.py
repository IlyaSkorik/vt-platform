"""In-memory fakes for the Applications application ports.

Framework-free, database-free test doubles that structurally satisfy the ports in
:mod:`apps.applications.application.interfaces`. Not a test module (no ``test_``
prefix), so pytest does not collect it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.applications.application.interfaces import (
    AdditionalServiceQuote,
    ApplicantInfo,
    EducationalOrganizationInfo,
    UploadConstraints,
)
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    ApplicationId,
    CompetitionId,
    CompetitionPriceQuote,
    EducationalOrganizationId,
    Money,
    ParticipantCountRange,
    PriceCalculationType,
    ReviewerId,
    ServiceId,
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
        accepts_payment: bool = True,
        accepts_upload: bool = True,
        policy: SubmissionParticipationPolicy | None = None,
        price: Money | None = None,
        calculation_type: PriceCalculationType = PriceCalculationType.PER_PARTICIPANT,
    ) -> None:
        self.known = known
        self.open_for_submissions = open_for_submissions
        self.accepts_payment_flag = accepts_payment
        self.accepts_upload_flag = accepts_upload
        self.policy: SubmissionParticipationPolicy | None = (
            policy
            if policy is not None
            else SubmissionParticipationPolicy(
                participant_count_range=ParticipantCountRange(min_count=1),
                is_admissible=True,
            )
        )
        self.price: Money | None = price if price is not None else Money.of("500.00")
        self.calculation_type = calculation_type

    def exists(self, competition_id: CompetitionId) -> bool:
        return self.known

    def accepts_submissions(self, *, competition_id: CompetitionId, nomination_id: object = None, now: datetime) -> bool:
        return self.open_for_submissions

    def accepts_payment(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        return self.accepts_payment_flag

    def accepts_upload(self, *, competition_id: CompetitionId, attachment_kind: str, now: datetime) -> bool:
        return self.accepts_upload_flag

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

    def price_quote(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: object,
        discipline_id: object,
        age_category_id: object,
        participant_group_id: object,
        participation_format_id: object,
    ) -> CompetitionPriceQuote | None:
        if self.price is None:
            return None
        return CompetitionPriceQuote(unit_price=self.price, calculation_type=self.calculation_type)


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


class FakeApplicationRepository:
    """In-memory :class:`ApplicationRepository` keyed by :class:`ApplicationId`."""

    def __init__(self) -> None:
        self._by_id: dict[ApplicationId, Application] = {}
        self.saved: list[Application] = []

    def get(self, application_id: ApplicationId) -> Application | None:
        return self._by_id.get(application_id)

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Application]:
        entries = [a for a in self._by_id.values() if a.applicant_id == applicant_id and not a.is_deleted]
        return sorted(entries, key=lambda a: a.created_at, reverse=True)

    def save(self, application: Application) -> None:
        self._by_id[application.id] = application
        self.saved.append(application)


class FakeCompetitionServiceCatalog:
    """Configurable Competition additional-service & consent ACL stand-in."""

    def __init__(
        self,
        *,
        service_price: Money | None = None,
        service_known: bool = True,
        required_consents: frozenset[str] = frozenset(),
        required_services: frozenset[str] = frozenset(),
        billing_model: PriceCalculationType = PriceCalculationType.PER_PARTICIPANT,
        available_format_ids: frozenset[str] = frozenset(),
        required_service: bool = False,
    ) -> None:
        self._service_price = service_price if service_price is not None else Money.of("25.00")
        self._service_known = service_known
        self._required = required_consents
        self._required_services = required_services
        self._billing_model = billing_model
        self._available_format_ids = available_format_ids
        self._required_service = required_service

    def get_additional_service(self, *, competition_id: CompetitionId, service_id: ServiceId) -> AdditionalServiceQuote | None:
        if not self._service_known:
            return None
        return AdditionalServiceQuote(
            service_id=service_id,
            name="Commemorative T-shirt",
            unit_price=self._service_price,
            billing_model=self._billing_model,
            available_format_ids=self._available_format_ids,
            required=self._required_service,
        )

    def required_consent_codes(self, *, competition_id: CompetitionId) -> frozenset[str]:
        return self._required

    def required_service_ids(self, *, competition_id: CompetitionId, participation_format_ids: frozenset[str]) -> frozenset[str]:
        return self._required_services


class FakeEducationalOrganizationDirectory:
    """Institutions ACL stand-in; resolves any id to a fixed org unless set unknown."""

    def __init__(self, *, known: bool = True, name: str = "Music School No.1") -> None:
        self._known = known
        self._name = name

    def get(self, *, organization_id: EducationalOrganizationId) -> EducationalOrganizationInfo | None:
        if not self._known:
            return None
        return EducationalOrganizationInfo(organization_id=organization_id.json(), name=self._name)


class FakeFileStorage:
    """In-memory :class:`FileStorage`; records saved objects, returns a fake key."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self._seq = 0

    def save(self, *, content: bytes, filename: str, content_type: str) -> str:
        self._seq += 1
        reference = f"applications/attachments/fake-{self._seq}/{filename}"
        self.saved[reference] = content
        return reference

    def delete(self, *, reference: str) -> None:
        self.deleted.append(reference)
        self.saved.pop(reference, None)


class FakeCompetitionUploadPolicy:
    """Configurable :class:`CompetitionUploadPolicy` stand-in (one constraint for all kinds)."""

    def __init__(self, *, max_bytes: int = 25 * 1024 * 1024, allowed_extensions: frozenset[str] = frozenset({"mp3", "pdf", "mp4", "png"})) -> None:
        self._max_bytes = max_bytes
        self._allowed = allowed_extensions

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        return UploadConstraints(max_bytes=self._max_bytes, allowed_extensions=self._allowed)
