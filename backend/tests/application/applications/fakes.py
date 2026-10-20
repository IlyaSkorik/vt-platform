"""In-memory fakes for the Applications application ports.

Framework-free, database-free test doubles that structurally satisfy the ports in
:mod:`apps.applications.application.interfaces`. Not a test module (no ``test_``
prefix), so pytest does not collect it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from apps.applications.application.interfaces import (
    AdditionalServiceQuote,
    ApplicantInfo,
    EducationalOrganizationInfo,
    ReceiptRequirement,
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
        additional_performance_discount_percent: int = 0,
        allows_multiple_performances: bool = True,
        collects_payer_details: bool = False,
        auto_cancels_unpaid_orders: bool = True,
        waitlisting_nominations: frozenset[str] = frozenset(),
        closed_nominations: frozenset[str] = frozenset(),
        editing_locked: bool = False,
    ) -> None:
        self.discount_percent = additional_performance_discount_percent
        self.multiple_performances = allows_multiple_performances
        self.payer_details = collects_payer_details
        self.auto_cancel_unpaid = auto_cancels_unpaid_orders
        self.known = known
        self.open_for_submissions = open_for_submissions
        #: Nominations whose registration has closed but which keep a waitlist, and
        #: nominations that closed with no list at all. Both are shut to ordinary
        #: submission; only the first has a second door.
        self.waitlisting_nominations = waitlisting_nominations
        self.closed_nominations = closed_nominations
        #: The organizer's festival-wide freeze. Off by default — it is a decision
        #: somebody takes, so a test that does not mention it has not taken it.
        self.editing_locked = editing_locked
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
        if nomination_id is not None and str(nomination_id) in (self.waitlisting_nominations | self.closed_nominations):
            return False
        return self.open_for_submissions

    def accepts_waitlist(self, *, competition_id: CompetitionId, nomination_id: object = None, now: datetime) -> bool:
        if nomination_id is None:
            return bool(self.waitlisting_nominations)
        return str(nomination_id) in self.waitlisting_nominations

    def accepts_payment(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        return self.accepts_payment_flag

    def is_editing_locked(self, *, competition_id: CompetitionId) -> bool:
        return self.editing_locked

    def accepts_upload(self, *, competition_id: CompetitionId, attachment_kind: str, now: datetime) -> bool:
        return self.accepts_upload_flag

    def additional_performance_discount_percent(self, *, competition_id: CompetitionId) -> int:
        return self.discount_percent

    def allows_multiple_performances(self, *, competition_id: CompetitionId) -> bool:
        return self.multiple_performances

    def auto_cancels_unpaid_orders(self, *, competition_id: CompetitionId) -> bool:
        return self.auto_cancel_unpaid

    def collects_payer_details(self, *, competition_id: CompetitionId) -> bool:
        return self.payer_details

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
        if self.policy is None:
            return None
        # Mirror the real ACL: whether the combination is priced is read off the same
        # pricing table `price_quote` answers from, so clearing `price` makes the
        # combination free rather than leaving an unsatisfiable policy behind.
        return replace(self.policy, is_priced=self.price is not None)

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


class RecordingApplicantNotifier:
    """Records which notice each order triggered, by the e-mail it was sent to."""

    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.waitlisted: list[str] = []
        self.awaiting_payment: list[str] = []
        #: The deadline each awaiting-payment notice carried, ``None`` where the
        #: competition does not auto-cancel and so names no date.
        self.awaiting_payment_deadlines: list[datetime | None] = []
        self.auto_cancelled: list[str] = []

    def notify_application_submitted(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        self.submitted.append(email)

    def notify_application_waitlisted(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        self.waitlisted.append(email)

    def notify_application_awaiting_payment(
        self, *, user_id: str, email: str, applicant_name: str, application_id: str, deadline: datetime | None
    ) -> None:
        self.awaiting_payment.append(email)
        self.awaiting_payment_deadlines.append(deadline)

    def notify_application_auto_cancelled(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        self.auto_cancelled.append(email)


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
        receipt_requirement: ReceiptRequirement | None = None,
        requires_parent_guardian: bool = False,
    ) -> None:
        self._requires_parent_guardian = requires_parent_guardian
        self._service_price = service_price if service_price is not None else Money.of("25.00")
        self._service_known = service_known
        self._required = required_consents
        self._required_services = required_services
        self._billing_model = billing_model
        self._available_format_ids = available_format_ids
        self._required_service = required_service
        self._receipt_requirement = receipt_requirement if receipt_requirement is not None else ReceiptRequirement.none()

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

    def requires_parent_guardian(self, *, competition_id: CompetitionId) -> bool:
        return self._requires_parent_guardian

    def required_service_ids(self, *, competition_id: CompetitionId, participation_format_ids: frozenset[str]) -> frozenset[str]:
        return self._required_services

    def receipt_requirement(
        self,
        *,
        competition_id: CompetitionId,
        participation_format_ids: frozenset[str],
    ) -> ReceiptRequirement:
        return self._receipt_requirement


class FakeParticipantGuardianRegistry:
    """Participants ACL stand-in; every participant either has a guardian or none do."""

    def __init__(self, *, all_covered: bool = True) -> None:
        self._all_covered = all_covered

    def participants_without_active_guardian(self, *, participant_ids: frozenset[str]) -> frozenset[str]:
        return frozenset() if self._all_covered else participant_ids


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

    def __init__(
        self,
        *,
        max_bytes: int = 25 * 1024 * 1024,
        allowed_extensions: frozenset[str] = frozenset({"mp3", "pdf", "mp4", "png", "jpg"}),
        shared_budget_kinds: frozenset[str] = frozenset(),
    ) -> None:
        self._max_bytes = max_bytes
        self._allowed = allowed_extensions
        self._shared = shared_budget_kinds

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        return UploadConstraints(
            max_bytes=self._max_bytes,
            allowed_extensions=self._allowed,
            shared_budget_kinds=self._shared,
        )
