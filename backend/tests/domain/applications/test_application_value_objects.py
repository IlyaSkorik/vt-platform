"""Unit tests for the Application (order) aggregate's value objects."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.applications.domain.exceptions import (
    InvalidApplicationIdError,
    InvalidApplicationStatusChangeError,
    InvalidConsentError,
    InvalidEducationalOrganizationIdError,
    InvalidOrganizationNameError,
    InvalidServiceIdError,
    InvalidServiceLineError,
    InvalidSubmissionRefError,
    InvalidTotalPriceSnapshotError,
)
from apps.applications.domain.value_objects import (
    ApplicationId,
    ApplicationStatus,
    ApplicationStatusChange,
    Consent,
    Currency,
    EducationalOrganizationId,
    Money,
    OrganizationName,
    PriceSnapshot,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionRef,
    SubmissionStatus,
    TotalPriceSnapshot,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


def _v7() -> uuid.UUID:
    return ApplicationId.generate().value


class TestIdentifiers:
    def test_application_id_roundtrips_through_string(self) -> None:
        app_id = ApplicationId.generate()
        assert ApplicationId.from_string(app_id.json()) == app_id

    def test_application_id_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidApplicationIdError):
            ApplicationId.from_uuid(uuid.uuid4())

    def test_application_id_rejects_garbage_string(self) -> None:
        with pytest.raises(InvalidApplicationIdError):
            ApplicationId.from_string("not-a-uuid")

    def test_educational_organization_id_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidEducationalOrganizationIdError):
            EducationalOrganizationId.from_uuid(uuid.uuid4())

    def test_service_id_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidServiceIdError):
            ServiceId.from_uuid(uuid.uuid4())


class TestOrganizationName:
    def test_trims_value(self) -> None:
        assert OrganizationName("  Music School No.1  ").value == "Music School No.1"

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidOrganizationNameError):
            OrganizationName("   ")

    def test_rejects_too_long(self) -> None:
        with pytest.raises(InvalidOrganizationNameError):
            OrganizationName("x" * 301)


class TestConsent:
    def test_trims_code_and_version(self) -> None:
        consent = Consent(code="  personal_data ", version=" v2 ", accepted_at=NOW)
        assert consent.code == "personal_data"
        assert consent.version == "v2"

    def test_rejects_empty_code(self) -> None:
        with pytest.raises(InvalidConsentError):
            Consent(code="  ", version="v1", accepted_at=NOW)

    def test_rejects_empty_version(self) -> None:
        with pytest.raises(InvalidConsentError):
            Consent(code="personal_data", version="", accepted_at=NOW)

    def test_rejects_non_datetime_accepted_at(self) -> None:
        with pytest.raises(InvalidConsentError):
            Consent(code="personal_data", version="v1", accepted_at="today")  # type: ignore[arg-type]


class TestServiceLine:
    def test_line_total_is_unit_times_quantity(self) -> None:
        line = ServiceLine(service_id=ServiceId.from_uuid(_v7()), name="T-shirt", unit_price=Money.of("25.00"), quantity=3)
        assert line.line_total == Money.of("75.00")

    def test_rejects_zero_quantity(self) -> None:
        with pytest.raises(InvalidServiceLineError):
            ServiceLine(service_id=ServiceId.from_uuid(_v7()), name="T-shirt", unit_price=Money.of("25.00"), quantity=0)

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(InvalidServiceLineError):
            ServiceLine(service_id=ServiceId.from_uuid(_v7()), name="  ", unit_price=Money.of("25.00"), quantity=1)

    def test_rejects_non_money_unit_price(self) -> None:
        with pytest.raises(InvalidServiceLineError):
            ServiceLine(service_id=ServiceId.from_uuid(_v7()), name="T-shirt", unit_price=Decimal("25.00"), quantity=1)  # type: ignore[arg-type]


class TestSubmissionRef:
    def _ref(self, *, status: SubmissionStatus, price: PriceSnapshot | None) -> SubmissionRef:
        return SubmissionRef(
            submission_id=SubmissionId.generate(),
            performance_title="Swan Lake",
            participant_display_name="Ivanova Anna",
            nomination="Choreography",
            discipline="Ballet",
            status=status,
            price=price,
        )

    def test_is_approved_reflects_status(self) -> None:
        assert self._ref(status=SubmissionStatus.APPROVED, price=None).is_approved is True
        assert self._ref(status=SubmissionStatus.UNDER_REVIEW, price=None).is_approved is False

    def test_price_line_is_zero_when_unpriced(self) -> None:
        assert self._ref(status=SubmissionStatus.DRAFT, price=None).price_line == Money.of("0.00")

    def test_price_line_reads_snapshot(self) -> None:
        snapshot = PriceSnapshot(price=Money.of("300.00"), calculated_at=NOW)
        assert self._ref(status=SubmissionStatus.APPROVED, price=snapshot).price_line == Money.of("300.00")

    def test_trims_display_labels(self) -> None:
        ref = SubmissionRef(
            submission_id=SubmissionId.generate(),
            performance_title="  Swan Lake  ",
            participant_display_name="  Ivanova Anna ",
            nomination=" Choreography ",
            discipline=" Ballet ",
            status=SubmissionStatus.DRAFT,
        )
        assert ref.performance_title == "Swan Lake"
        assert ref.discipline == "Ballet"

    def test_rejects_over_long_label(self) -> None:
        with pytest.raises(InvalidSubmissionRefError):
            SubmissionRef(
                submission_id=SubmissionId.generate(),
                performance_title="x" * 301,
                participant_display_name="Ivanova Anna",
                nomination="Choreography",
                discipline="Ballet",
                status=SubmissionStatus.DRAFT,
            )

    def test_rejects_bad_status_type(self) -> None:
        with pytest.raises(InvalidSubmissionRefError):
            SubmissionRef(
                submission_id=SubmissionId.generate(),
                performance_title="Swan Lake",
                participant_display_name="Ivanova Anna",
                nomination="Choreography",
                discipline="Ballet",
                status="APPROVED",  # type: ignore[arg-type]
            )


class TestTotalPriceSnapshot:
    def test_exposes_amount_and_currency(self) -> None:
        snapshot = TotalPriceSnapshot(
            total=Money.of("375.00"),
            submissions_total=Money.of("300.00"),
            services_total=Money.of("75.00"),
            calculated_at=NOW,
        )
        assert snapshot.amount == Decimal("375.00")
        assert snapshot.currency is Currency.BYN

    def test_rejects_non_money_component(self) -> None:
        with pytest.raises(InvalidTotalPriceSnapshotError):
            TotalPriceSnapshot(
                total=Money.of("375.00"),
                submissions_total="300.00",  # type: ignore[arg-type]
                services_total=Money.of("75.00"),
                calculated_at=NOW,
            )

    def test_rejects_non_datetime_calculated_at(self) -> None:
        with pytest.raises(InvalidTotalPriceSnapshotError):
            TotalPriceSnapshot(
                total=Money.of("375.00"),
                submissions_total=Money.of("300.00"),
                services_total=Money.of("75.00"),
                calculated_at="now",  # type: ignore[arg-type]
            )


class TestApplicationStatusChange:
    def test_records_transition(self) -> None:
        change = ApplicationStatusChange(from_status=ApplicationStatus.DRAFT, to_status=ApplicationStatus.SUBMITTED, occurred_at=NOW)
        assert change.from_status is ApplicationStatus.DRAFT
        assert change.to_status is ApplicationStatus.SUBMITTED

    def test_allows_null_origin_for_creation(self) -> None:
        change = ApplicationStatusChange(from_status=None, to_status=ApplicationStatus.DRAFT, occurred_at=NOW)
        assert change.from_status is None

    def test_rejects_bad_target(self) -> None:
        with pytest.raises(InvalidApplicationStatusChangeError):
            ApplicationStatusChange(from_status=None, to_status="DRAFT", occurred_at=NOW)  # type: ignore[arg-type]
