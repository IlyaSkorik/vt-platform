"""Use-case tests for the organization module switchboard."""

from __future__ import annotations

import pytest

from apps.organization.application.exceptions import InvalidInputError, OrganizationNotFoundError
from apps.organization.application.handlers import (
    SetOrganizationModulesCommand,
    SetOrganizationModulesHandler,
)
from apps.organization.application.read_models import EnabledModulesReader
from apps.organization.composition import (
    build_list_organization_modules_handler,
    build_set_organization_modules_handler,
)
from apps.organization.domain.value_objects import OrganizationId, OrganizationModule
from apps.organization.infrastructure.repositories import (
    DjangoModuleEntitlementRepository,
    DjangoOrganizationRepository,
)

pytestmark = pytest.mark.django_db


def _organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


def _set(modules: tuple[str, ...], *, handler: SetOrganizationModulesHandler | None = None) -> None:
    (handler or build_set_organization_modules_handler()).handle(SetOrganizationModulesCommand(organization_id=_organization_id(), modules=modules))


def _enabled() -> frozenset[OrganizationModule]:
    return DjangoModuleEntitlementRepository().enabled_modules(OrganizationId.from_string(_organization_id()))


#: The modules the grandfathering migration named, spelled out as it spells them.
#:
#: Not ``frozenset(OrganizationModule)``: the migration is frozen to the modules that
#: existed when it ran, and deliberately so — a module added later must not be handed
#: retroactively to organizations the migration already passed over (see its docstring,
#: 0008_grant_every_module_to_existing_organizations).
_GRANDFATHERED = frozenset(
    {
        OrganizationModule.COMPETITIONS,
        OrganizationModule.APPLICATIONS,
        OrganizationModule.PARTICIPANTS,
        OrganizationModule.JURY,
        OrganizationModule.PROGRAMS,
        OrganizationModule.DIPLOMAS,
        OrganizationModule.VOTING,
        OrganizationModule.FINANCE,
        OrganizationModule.ANALYTICS,
    }
)


class TestTheSwitchboard:
    def test_the_migration_grandfathered_the_modules_that_existed_then(self) -> None:
        """Existing organizations must not lose the panel they had yesterday."""
        assert _enabled() == _GRANDFATHERED

    def test_a_module_added_later_is_not_granted_retroactively(self) -> None:
        """Новый модуль — это то, что оператор включает, а не то, что все уже держат."""
        added_later = frozenset(OrganizationModule) - _GRANDFATHERED

        assert added_later and not (added_later & _enabled())

    def test_setting_a_subset_turns_everything_else_off(self) -> None:
        _set(("VOTING",))

        assert _enabled() == frozenset({OrganizationModule.VOTING})

    def test_the_view_lists_every_module_including_the_withheld_ones(self) -> None:
        _set(("VOTING",))

        view = build_list_organization_modules_handler().handle(_organization_id())

        assert len(view.modules) == len(OrganizationModule)
        by_name = {row.module: row for row in view.modules}
        assert by_name["VOTING"].enabled is True
        assert by_name["FINANCE"].enabled is False
        assert by_name["FINANCE"].disabled_at is not None

    def test_re_saving_the_same_set_keeps_the_date_the_module_was_sold(self) -> None:
        _set(("VOTING",))
        first = {row.module: row for row in build_list_organization_modules_handler().handle(_organization_id()).modules}

        _set(("VOTING",))
        second = {row.module: row for row in build_list_organization_modules_handler().handle(_organization_id()).modules}

        assert second["VOTING"].enabled_at == first["VOTING"].enabled_at

    def test_turning_everything_off_is_expressible(self) -> None:
        _set(())

        assert _enabled() == frozenset()

    def test_an_unknown_module_is_refused(self) -> None:
        with pytest.raises(InvalidInputError):
            _set(("TELEPATHY",))

    def test_an_unknown_organization_is_refused(self) -> None:
        with pytest.raises(OrganizationNotFoundError):
            build_set_organization_modules_handler().handle(
                SetOrganizationModulesCommand(organization_id=str(OrganizationId.generate()), modules=("VOTING",))
            )


class TestTheReadService:
    def test_it_reports_what_the_operator_switched_on(self) -> None:
        _set(("VOTING", "PROGRAMS"))
        reader = EnabledModulesReader(entitlements=DjangoModuleEntitlementRepository())

        modules = reader.for_organization(OrganizationId.from_string(_organization_id()).value)

        assert modules == frozenset({"VOTING", "PROGRAMS"})

    def test_an_unknown_module_name_is_simply_not_held(self) -> None:
        reader = EnabledModulesReader(entitlements=DjangoModuleEntitlementRepository())

        assert (
            reader.is_enabled(
                organization_id=OrganizationId.from_string(_organization_id()).value,
                module="TELEPATHY",
            )
            is False
        )

    def test_withdrawing_a_module_takes_effect_despite_the_cache(self) -> None:
        """The writer invalidates, so a revoked module stops working at once."""
        organization_uuid = OrganizationId.from_string(_organization_id()).value
        from apps.organization.composition import build_enabled_modules_read_service

        assert build_enabled_modules_read_service().is_enabled(organization_id=organization_uuid, module="VOTING")

        _set(("PROGRAMS",))

        assert not build_enabled_modules_read_service().is_enabled(organization_id=organization_uuid, module="VOTING")
