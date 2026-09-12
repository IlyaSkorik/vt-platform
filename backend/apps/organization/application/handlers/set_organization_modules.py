"""Which parts of the platform an organization holds — the operator's decision.

Two platform-level use cases: read the switchboard, and move switches on it. Like
the commercial terms next door in :mod:`.connect_organization`, they live in the
Organization context because the data is the organization's, but they are reachable
only by a platform operator: what an organization was sold is the platform's call.

Both are expressed over the *whole* switchboard rather than one module at a time.
The console renders every module with its state, and a save posts back the set that
should be on; anything absent is off. That makes the operation idempotent and free
of ordering surprises — and makes "turn everything off" expressible, which a
per-module toggle endpoint cannot do in one atomic step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.organization.application.exceptions import (
    OrganizationNotFoundError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    ModuleEntitlementRepository,
    OrganizationRepository,
    UuidGenerator,
)
from apps.organization.application.read_models import ModuleCache
from apps.organization.domain.entities import ModuleEntitlement
from apps.organization.domain.value_objects import (
    ModuleEntitlementId,
    OrganizationId,
    OrganizationModule,
    StaffUserId,
)

__all__ = [
    "ListOrganizationModulesHandler",
    "ModuleView",
    "OrganizationModulesView",
    "SetOrganizationModulesCommand",
    "SetOrganizationModulesHandler",
]


@dataclass(frozen=True, slots=True)
class ModuleView:
    """One module as the console shows it: its name, its state, and its history."""

    module: str
    enabled: bool
    enabled_at: datetime | None = None
    disabled_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OrganizationModulesView:
    """The whole switchboard for one organization.

    Every module the platform knows appears here, held or not, so the console never
    has to reconcile a list of rows against a list of possible modules — and so a
    module introduced after the organization was connected shows up switched off
    rather than not at all.
    """

    organization_id: str
    modules: tuple[ModuleView, ...]


@dataclass(frozen=True, slots=True)
class SetOrganizationModulesCommand:
    """Turn on exactly ``modules`` for the organization, and turn off everything else."""

    organization_id: str
    modules: tuple[str, ...]
    #: The platform operator making the change, recorded on the entitlement.
    changed_by: str | None = None


def _view(organization_id: OrganizationId, entitlements: dict[OrganizationModule, ModuleEntitlement]) -> OrganizationModulesView:
    """Project the decided entitlements onto the full module roster."""
    return OrganizationModulesView(
        organization_id=organization_id.json(),
        modules=tuple(
            ModuleView(
                module=module.value,
                enabled=entitlement.enabled if entitlement is not None else False,
                enabled_at=entitlement.enabled_at if entitlement is not None else None,
                disabled_at=entitlement.disabled_at if entitlement is not None else None,
            )
            for module in OrganizationModule
            for entitlement in (entitlements.get(module),)
        ),
    )


class ListOrganizationModulesHandler:
    """Use case: read one organization's module switchboard."""

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        entitlements: ModuleEntitlementRepository,
    ) -> None:
        self._organizations = organizations
        self._entitlements = entitlements

    def handle(self, organization_id: str) -> OrganizationModulesView:
        with translate_domain_errors():
            parsed = OrganizationId.from_string(organization_id)

        if self._organizations.get(parsed) is None:
            raise OrganizationNotFoundError("Организация не найдена.")

        decided = {entitlement.module: entitlement for entitlement in self._entitlements.list_by_organization(parsed)}
        return _view(parsed, decided)


class SetOrganizationModulesHandler:
    """Use case: set an organization's modules to exactly the given set.

    Idempotent end to end. Each entitlement decides for itself whether anything
    changed (an already-on module returns no event and keeps the date it was first
    sold), so re-saving an unchanged console publishes nothing and rewrites nothing.

    A module never decided about is *created* on the way through — enabled if it is
    in the set, explicitly withheld if it is not. Writing the "no" down is what makes
    the console show a decision rather than a blank, and what gives the operator a
    date when they later change their mind.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        entitlements: ModuleEntitlementRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
        cache: ModuleCache | None = None,
    ) -> None:
        self._organizations = organizations
        self._entitlements = entitlements
        self._clock = clock
        self._uuids = uuids
        self._events = events
        self._cache = cache

    def handle(self, command: SetOrganizationModulesCommand) -> OrganizationModulesView:
        with translate_domain_errors():
            organization_id = OrganizationId.from_string(command.organization_id)
            wanted = frozenset(OrganizationModule.parse(name) for name in command.modules)
            changed_by = StaffUserId.from_string(command.changed_by) if command.changed_by else None

        if self._organizations.get(organization_id) is None:
            raise OrganizationNotFoundError("Организация не найдена.")

        now = self._clock.utcnow()
        decided = {entitlement.module: entitlement for entitlement in self._entitlements.list_by_organization(organization_id)}
        produced = []

        for module in OrganizationModule:
            should_be_on = module in wanted
            entitlement = decided.get(module)

            if entitlement is None:
                # Nothing decided yet: create the row either way, so the console shows
                # a decision and a later change has something to compare against.
                if should_be_on:
                    entitlement, events = ModuleEntitlement.grant(
                        entitlement_id=ModuleEntitlementId.from_uuid(self._uuids.new()),
                        organization_id=organization_id,
                        module=module,
                        granted_by=changed_by,
                        now=now,
                    )
                else:
                    entitlement = ModuleEntitlement.withheld(
                        entitlement_id=ModuleEntitlementId.from_uuid(self._uuids.new()),
                        organization_id=organization_id,
                        module=module,
                        now=now,
                    )
                    events = []
                self._entitlements.save(entitlement)
                decided[module] = entitlement
                produced.extend(events)
                continue

            events = entitlement.enable(changed_by=changed_by, now=now) if should_be_on else entitlement.disable(changed_by=changed_by, now=now)
            if events:
                self._entitlements.save(entitlement)
                produced.extend(events)

        # Invalidate before publishing: a subscriber that reacts by reading the
        # switchboard must not be served the set that was true a moment ago.
        if self._cache is not None:
            self._cache.invalidate(organization_id.value)
        if produced:
            self._events.publish(produced)

        return _view(organization_id, decided)
