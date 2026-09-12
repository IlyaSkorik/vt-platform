"""Unit tests for the ``ModuleEntitlement`` entity and the module value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.organization.domain.entities import ModuleEntitlement
from apps.organization.domain.events import (
    OrganizationModuleDisabled,
    OrganizationModuleEnabled,
)
from apps.organization.domain.exceptions import (
    DirectConstructionError,
    InvalidOrganizationModuleError,
)
from apps.organization.domain.value_objects import (
    ModuleEntitlementId,
    OrganizationId,
    OrganizationModule,
    StaffUserId,
)

NOW = datetime(2026, 9, 12, 10, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=30)


def _organization_id() -> OrganizationId:
    return OrganizationId.generate()


def _operator() -> StaffUserId:
    return StaffUserId.from_uuid(OrganizationId.generate().value)


def _granted(module: OrganizationModule = OrganizationModule.VOTING) -> ModuleEntitlement:
    entitlement, _ = ModuleEntitlement.grant(
        entitlement_id=ModuleEntitlementId.generate(),
        organization_id=_organization_id(),
        module=module,
        granted_by=_operator(),
        now=NOW,
    )
    return entitlement


class TestModuleValueObject:
    def test_parse_accepts_a_known_module(self) -> None:
        assert OrganizationModule.parse("VOTING") is OrganizationModule.VOTING

    def test_parse_rejects_an_unknown_module(self) -> None:
        with pytest.raises(InvalidOrganizationModuleError):
            OrganizationModule.parse("TELEPATHY")

    def test_members_serialize_to_their_own_wire_value(self) -> None:
        assert OrganizationModule.VOTING == "VOTING"


class TestGrant:
    def test_grant_creates_an_enabled_entitlement_and_an_event(self) -> None:
        organization_id = _organization_id()
        operator = _operator()

        entitlement, events = ModuleEntitlement.grant(
            entitlement_id=ModuleEntitlementId.generate(),
            organization_id=organization_id,
            module=OrganizationModule.VOTING,
            granted_by=operator,
            now=NOW,
        )

        assert entitlement.enabled is True
        assert entitlement.enabled_at == NOW
        assert entitlement.enabled_by == operator
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, OrganizationModuleEnabled)
        assert event.aggregate_id == organization_id.value
        assert event.module is OrganizationModule.VOTING

    def test_withheld_creates_a_disabled_entitlement_without_an_event(self) -> None:
        entitlement = ModuleEntitlement.withheld(
            entitlement_id=ModuleEntitlementId.generate(),
            organization_id=_organization_id(),
            module=OrganizationModule.FINANCE,
            now=NOW,
        )

        assert entitlement.enabled is False
        assert entitlement.enabled_at is None

    def test_direct_construction_is_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            ModuleEntitlement(
                _token=object(),
                _id=ModuleEntitlementId.generate(),
                _organization_id=_organization_id(),
                _module=OrganizationModule.VOTING,
                _enabled=True,
                _created_at=NOW,
                _updated_at=NOW,
            )


class TestToggling:
    def test_disabling_an_enabled_module_records_who_and_when(self) -> None:
        entitlement = _granted()
        operator = _operator()

        events = entitlement.disable(changed_by=operator, now=LATER)

        assert entitlement.enabled is False
        assert entitlement.disabled_at == LATER
        assert entitlement.disabled_by == operator
        assert [type(event) for event in events] == [OrganizationModuleDisabled]

    def test_disabling_keeps_the_date_the_module_was_first_sold(self) -> None:
        entitlement = _granted()

        entitlement.disable(changed_by=_operator(), now=LATER)

        assert entitlement.enabled_at == NOW

    def test_disabling_an_already_disabled_module_is_a_no_op(self) -> None:
        entitlement = ModuleEntitlement.withheld(
            entitlement_id=ModuleEntitlementId.generate(),
            organization_id=_organization_id(),
            module=OrganizationModule.VOTING,
            now=NOW,
        )
        version_before = entitlement.version

        assert entitlement.disable(changed_by=_operator(), now=LATER) == []
        assert entitlement.version == version_before

    def test_re_enabling_an_enabled_module_does_not_move_the_billing_date(self) -> None:
        entitlement = _granted()

        assert entitlement.enable(changed_by=_operator(), now=LATER) == []
        assert entitlement.enabled_at == NOW

    def test_re_enabling_after_a_withdrawal_clears_the_withdrawal(self) -> None:
        entitlement = _granted()
        entitlement.disable(changed_by=_operator(), now=LATER)

        events = entitlement.enable(changed_by=_operator(), now=LATER + timedelta(days=1))

        assert entitlement.enabled is True
        assert entitlement.disabled_at is None
        assert entitlement.disabled_by is None
        assert [type(event) for event in events] == [OrganizationModuleEnabled]

    def test_each_toggle_bumps_the_version(self) -> None:
        entitlement = _granted()
        version_before = entitlement.version

        entitlement.disable(changed_by=_operator(), now=LATER)

        assert entitlement.version == version_before + 1


class TestRehydration:
    def test_rehydrate_restores_state_without_events(self) -> None:
        original = _granted()
        original.disable(changed_by=_operator(), now=LATER)

        restored = ModuleEntitlement.rehydrate(
            entitlement_id=original.id,
            organization_id=original.organization_id,
            module=original.module,
            enabled=original.enabled,
            created_at=original.created_at,
            updated_at=original.updated_at,
            enabled_at=original.enabled_at,
            enabled_by=original.enabled_by,
            disabled_at=original.disabled_at,
            disabled_by=original.disabled_by,
            version=original.version,
        )

        assert restored == original
        assert restored.enabled is False
        assert restored.version == original.version
