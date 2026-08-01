"""Unit tests for the ``PlatformAdministrator`` aggregate and the commission rate.

Two small pieces of domain, both load-bearing: who may operate the platform, and
what an organization owes it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.organization.domain.entities import Organization
from apps.organization.domain.events import OrganizationCommissionRateChanged, OrganizationConnected
from apps.organization.domain.exceptions import InvalidCommissionRateError
from apps.organization.domain.value_objects import (
    CommissionRate,
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
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
            PlatformAdministrator(  # type: ignore[call-arg]
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


class TestConnectingAnOrganization:
    def _connected(self, *, commission: str = "10") -> tuple[Organization, list]:
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

    def test_the_rate_can_be_renegotiated_while_suspended(self) -> None:
        # Suspension is often exactly why the terms are being revisited.
        organization, _ = self._connected(commission="10")
        organization.suspend(now=LATER)

        organization.change_commission_rate(CommissionRate.of("5"), now=LATER)

        assert organization.commission_rate.percent == Decimal("5.00")
