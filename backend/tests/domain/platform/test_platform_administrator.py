"""Unit tests for the ``PlatformAdministrator`` aggregate and the commercial terms.

Two small pieces of domain, both load-bearing: who may operate the platform, and
what an organization owes it — a share of its fees, or a flat price per performance.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.organization.domain.entities import Organization
from apps.organization.domain.events import (
    DomainEvent,
    OrganizationCommissionRateChanged,
    OrganizationConnected,
    OrganizationFeeScheduleChanged,
)
from apps.organization.domain.exceptions import (
    InvalidCommissionRateError,
    InvalidPerformanceFeeScheduleError,
    InvalidPerformanceFeeTierError,
)
from apps.organization.domain.value_objects import (
    BillingModel,
    CommissionRate,
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
    PerformanceFeeSchedule,
    PerformanceFeeTier,
)
from apps.platform.domain.entities import PlatformAdministrator
from apps.platform.domain.exceptions import (
    AdministratorAlreadyActiveError,
    AdministratorAlreadyRevokedError,
    DirectConstructionError,
    InvalidPlatformUserIdError,
)
from apps.platform.domain.value_objects import PlatformAdministratorId, PlatformUserId

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=30)


def _grant() -> PlatformAdministrator:
    return PlatformAdministrator.grant(
        administrator_id=PlatformAdministratorId.generate(),
        user_id=PlatformUserId.from_uuid(PlatformAdministratorId.generate().value),
        now=NOW,
    )


class TestPlatformAdministrator:
    def test_a_fresh_grant_is_active(self) -> None:
        administrator = _grant()
        assert administrator.is_active()
        assert administrator.granted_at == NOW
        assert administrator.revoked_at is None

    def test_revoking_keeps_the_record(self) -> None:
        # Deliberately not a delete: who could read across every organization,
        # and until when, has to stay answerable.
        administrator = _grant()
        administrator.revoke(now=LATER)

        assert administrator.is_active() is False
        assert administrator.revoked_at == LATER
        assert administrator.granted_at == NOW

    def test_revoking_twice_is_refused(self) -> None:
        administrator = _grant()
        administrator.revoke(now=LATER)
        with pytest.raises(AdministratorAlreadyRevokedError):
            administrator.revoke(now=LATER)

    def test_regranting_restores_the_same_record(self) -> None:
        administrator = _grant()
        administrator.revoke(now=LATER)
        administrator.regrant(now=LATER)

        assert administrator.is_active()
        assert administrator.granted_at == LATER

    def test_regranting_an_active_grant_is_refused(self) -> None:
        with pytest.raises(AdministratorAlreadyActiveError):
            _grant().regrant(now=LATER)

    def test_direct_construction_is_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            PlatformAdministrator(
                _token=object(),
                _id=PlatformAdministratorId.generate(),
                _user_id=PlatformUserId.from_uuid(PlatformAdministratorId.generate().value),
                _granted_at=NOW,
                _created_at=NOW,
                _updated_at=NOW,
            )

    def test_a_non_v7_reference_is_refused(self) -> None:
        with pytest.raises(InvalidPlatformUserIdError):
            PlatformUserId.from_string("not-a-uuid")


class TestCommissionRate:
    def test_a_rate_is_exact_and_two_scaled(self) -> None:
        assert CommissionRate.of("12.5").percent == Decimal("12.50")

    def test_zero_is_a_legitimate_rate(self) -> None:
        # An organization can be hosted for free; that is a term, not a mistake.
        assert CommissionRate.zero().percent == Decimal("0.00")

    def test_a_rate_outside_the_range_is_refused(self) -> None:
        with pytest.raises(InvalidCommissionRateError):
            CommissionRate.of("101")
        with pytest.raises(InvalidCommissionRateError):
            CommissionRate.of("-1")

    def test_a_float_is_refused(self) -> None:
        # Floats and money do not mix, and this number multiplies money.
        with pytest.raises(InvalidCommissionRateError):
            CommissionRate(12.5)  # type: ignore[arg-type]

    def test_applying_rounds_to_the_minor_unit(self) -> None:
        assert CommissionRate.of("12.5").apply_to(Decimal("333.33")) == Decimal("41.67")
        assert CommissionRate.zero().apply_to(Decimal("999.99")) == Decimal("0.00")


class TestPerformanceFeeSchedule:
    def _schedule(self) -> PerformanceFeeSchedule:
        # The terms as an operator writes them down: a solo, a small group, the rest.
        return PerformanceFeeSchedule.of([(1, 1, "2.50"), (2, 5, "4.00"), (6, None, "6.00")])

    def test_a_band_prices_the_headcount_it_covers(self) -> None:
        schedule = self._schedule()

        assert [schedule.fee_for(count) for count in (1, 2, 5, 6, 40)] == [
            Decimal("2.50"),
            Decimal("4.00"),
            Decimal("4.00"),
            Decimal("6.00"),
            Decimal("6.00"),
        ]

    def test_an_order_costs_the_sum_of_its_performances(self) -> None:
        # A solo, a duet and an eight-strong ensemble in one order.
        assert self._schedule().total_for([1, 2, 8]) == Decimal("12.50")

    def test_bands_are_stored_sorted_so_the_order_they_arrive_in_does_not_matter(self) -> None:
        shuffled = PerformanceFeeSchedule.of([(6, None, "6.00"), (1, 1, "2.50"), (2, 5, "4.00")])

        assert shuffled == self._schedule()
        assert str(shuffled) == "1: 2.50 BYN; 2-5: 4.00 BYN; 6+: 6.00 BYN"

    def test_a_gap_between_bands_is_refused(self) -> None:
        # A hole would bill some performances nothing at all, silently.
        with pytest.raises(InvalidPerformanceFeeScheduleError):
            PerformanceFeeSchedule.of([(1, 1, "2.50"), (3, None, "4.00")])

    def test_an_overlap_between_bands_is_refused(self) -> None:
        with pytest.raises(InvalidPerformanceFeeScheduleError):
            PerformanceFeeSchedule.of([(1, 5, "2.50"), (3, None, "4.00")])

    def test_a_schedule_must_start_at_one_participant(self) -> None:
        with pytest.raises(InvalidPerformanceFeeScheduleError):
            PerformanceFeeSchedule.of([(2, None, "4.00")])

    def test_the_top_band_must_be_open_ended(self) -> None:
        # Otherwise a bigger ensemble than anyone foresaw is priced at nothing.
        with pytest.raises(InvalidPerformanceFeeScheduleError):
            PerformanceFeeSchedule.of([(1, 5, "4.00")])

    def test_an_empty_schedule_is_refused(self) -> None:
        with pytest.raises(InvalidPerformanceFeeScheduleError):
            PerformanceFeeSchedule.of([])

    def test_a_float_price_is_refused(self) -> None:
        # Same rule as the commission rate: floats and money do not mix.
        with pytest.raises(InvalidPerformanceFeeTierError):
            PerformanceFeeTier(min_participants=1, max_participants=None, amount=2.5)  # type: ignore[arg-type]

    def test_a_band_below_one_participant_is_refused(self) -> None:
        with pytest.raises(InvalidPerformanceFeeTierError):
            PerformanceFeeTier.of(0, None, "1.00")

    def test_a_band_whose_top_is_below_its_bottom_is_refused(self) -> None:
        with pytest.raises(InvalidPerformanceFeeTierError):
            PerformanceFeeTier.of(5, 2, "1.00")


class TestConnectingAnOrganization:
    def _connected(self, *, commission: str = "10") -> tuple[Organization, list[DomainEvent]]:
        return Organization.connect(
            organization_id=OrganizationId.generate(),
            name=OrganizationName("Звёздный дождь"),
            slug=OrganizationSlug("zvezdnyy-dozhd"),
            commission_rate=CommissionRate.of(commission),
            now=NOW,
        )

    def test_a_connected_organization_starts_active_under_its_terms(self) -> None:
        organization, events = self._connected(commission="12.5")

        assert organization.status is OrganizationStatus.ACTIVE
        assert organization.commission_rate.percent == Decimal("12.50")
        assert isinstance(events[0], OrganizationConnected)

    def test_changing_the_rate_emits_the_fact(self) -> None:
        organization, _ = self._connected(commission="10")

        events = organization.change_commission_rate(CommissionRate.of("15"), now=LATER)

        assert organization.commission_rate.percent == Decimal("15.00")
        assert isinstance(events[0], OrganizationCommissionRateChanged)

    def test_setting_the_same_rate_changes_nothing(self) -> None:
        # Re-saving a form is not a renegotiation: no version bump, no event.
        organization, _ = self._connected(commission="10")
        version = organization.version

        assert organization.change_commission_rate(CommissionRate.of("10.00"), now=LATER) == []
        assert organization.version == version

    def test_an_organization_can_be_connected_on_the_per_performance_fee(self) -> None:
        schedule = PerformanceFeeSchedule.of([(1, 1, "2.50"), (2, None, "4.00")])

        organization, events = Organization.connect(
            organization_id=OrganizationId.generate(),
            name=OrganizationName("Звёздный дождь"),
            slug=OrganizationSlug("zvezdnyy-dozhd"),
            commission_rate=CommissionRate.zero(),
            fee_schedule=schedule,
            now=NOW,
        )

        # The model is derived from the terms, so "percent with a price list" cannot exist.
        assert organization.billing_model is BillingModel.PER_PERFORMANCE_FEE
        assert organization.fee_schedule == schedule
        assert isinstance(events[0], OrganizationConnected)

    def test_setting_a_schedule_moves_the_organization_onto_that_model(self) -> None:
        organization, _ = self._connected(commission="10")
        schedule = PerformanceFeeSchedule.of([(1, None, "3.00")])

        events = organization.change_fee_schedule(schedule, now=LATER)

        assert organization.billing_model is BillingModel.PER_PERFORMANCE_FEE
        assert isinstance(events[0], OrganizationFeeScheduleChanged)
        # The percentage last agreed is remembered, not erased.
        assert organization.commission_rate.percent == Decimal("10.00")

    def test_setting_a_rate_moves_it_back(self) -> None:
        organization, _ = self._connected(commission="10")
        organization.change_fee_schedule(PerformanceFeeSchedule.of([(1, None, "3.00")]), now=LATER)

        events = organization.change_commission_rate(CommissionRate.of("10"), now=LATER)

        # The rate is unchanged, but the model is not: this is still a renegotiation.
        assert organization.billing_model is BillingModel.COMMISSION_PERCENT
        assert isinstance(events[0], OrganizationCommissionRateChanged)

    def test_setting_the_same_schedule_changes_nothing(self) -> None:
        organization, _ = self._connected(commission="10")
        schedule = PerformanceFeeSchedule.of([(1, None, "3.00")])
        organization.change_fee_schedule(schedule, now=LATER)
        version = organization.version

        assert organization.change_fee_schedule(schedule, now=LATER) == []
        assert organization.version == version

    def test_the_rate_can_be_renegotiated_while_suspended(self) -> None:
        # Suspension is often exactly why the terms are being revisited.
        organization, _ = self._connected(commission="10")
        organization.suspend(now=LATER)

        organization.change_commission_rate(CommissionRate.of("5"), now=LATER)

        assert organization.commission_rate.percent == Decimal("5.00")
