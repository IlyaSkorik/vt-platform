"""Connecting an organization to the platform, and the terms it runs under.

Three platform-level use cases. They live in the Organization context because the
aggregate they touch is the Organization — but none of them is reachable by an
organization's own staff: the presentation edge gates them behind platform-operator
access, because "who may run festivals here, and for what cut" is the platform's
decision, not an organization's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from apps.organization.application.dto import InvitationView
from apps.organization.application.exceptions import (
    InvalidInputError,
    OrganizationConflictError,
    OrganizationNotFoundError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    ModuleEntitlementRepository,
    OrganizationRepository,
    StaffInvitationRepository,
    TokenHasher,
    UuidGenerator,
)
from apps.organization.domain.entities import ModuleEntitlement, Organization, StaffInvitation
from apps.organization.domain.events import DomainEvent
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    CommissionRate,
    ModuleEntitlementId,
    OrganizationId,
    OrganizationModule,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
    PerformanceFeeSchedule,
    StaffEmail,
    StaffInvitationId,
    StaffRole,
    StaffUserId,
)

__all__ = [
    "ChangeOrganizationStatusCommand",
    "ChangeOrganizationStatusHandler",
    "ConnectOrganizationCommand",
    "ConnectOrganizationHandler",
    "ConnectedOrganizationDto",
    "FeeTierRow",
    "ListOrganizationsHandler",
    "OrganizationSummaryView",
    "SetCommissionRateCommand",
    "SetCommissionRateHandler",
    "SetPerformanceFeeScheduleCommand",
    "SetPerformanceFeeScheduleHandler",
]


@dataclass(frozen=True, slots=True)
class FeeTierRow:
    """One band of a per-performance fee schedule, as flat primitives.

    The wire shape of a band in both directions — inbound on a command, outbound on
    a read view — so neither the caller nor the reader has to know the domain value
    object. ``max_participants`` of ``None`` is the open-ended top band.
    """

    min_participants: int
    max_participants: int | None
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ConnectOrganizationCommand:
    """Connect a new organization and invite the person who will run it.

    ``owner_email`` receives the invitation that makes them the organization's
    first OWNER; ``connected_by`` is the platform administrator doing it, recorded
    as the inviter.
    """

    name: str
    slug: str
    owner_email: str
    commission_percent: Decimal
    connected_by: str
    #: Supplying bands connects the organization on the per-performance fee model;
    #: leaving them empty connects it on the percentage one.
    fee_tiers: tuple[FeeTierRow, ...] = ()
    #: Which parts of the platform the organization is being sold. ``None`` means
    #: all of them — the full-access preset, and what connecting meant before the
    #: platform was sold in parts. An empty tuple is a different instruction and is
    #: honoured literally: an organization with no modules at all.
    modules: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class SetCommissionRateCommand:
    """Set what share of its participation fees an organization owes the platform."""

    organization_id: str
    commission_percent: Decimal


@dataclass(frozen=True, slots=True)
class SetPerformanceFeeScheduleCommand:
    """Bill an organization a flat fee per performance, on these bands."""

    organization_id: str
    tiers: tuple[FeeTierRow, ...]


@dataclass(frozen=True, slots=True)
class ChangeOrganizationStatusCommand:
    """Suspend a connected organization, or bring a suspended one back."""

    organization_id: str
    status: str


@dataclass(frozen=True, slots=True)
class OrganizationSummaryView:
    """A flat read view of one organization as the platform operator sees it."""

    id: str
    name: str
    slug: str
    status: str
    billing_model: str
    commission_percent: Decimal
    fee_tiers: tuple[FeeTierRow, ...]
    created_at: datetime

    @classmethod
    def from_organization(cls, organization: Organization) -> OrganizationSummaryView:
        schedule = organization.fee_schedule
        return cls(
            id=organization.id.json(),
            name=organization.name.value,
            slug=organization.slug.value,
            status=organization.status.value,
            billing_model=organization.billing_model.value,
            commission_percent=organization.commission_rate.percent,
            fee_tiers=()
            if schedule is None
            else tuple(
                FeeTierRow(
                    min_participants=tier.min_participants,
                    max_participants=tier.max_participants,
                    amount=tier.amount,
                )
                for tier in schedule.tiers
            ),
            created_at=organization.created_at,
        )


@dataclass(frozen=True, slots=True)
class ConnectedOrganizationDto:
    """The outcome of connecting an organization: the organization and its owner invitation."""

    organization: OrganizationSummaryView
    owner_invitation: InvitationView


def _schedule_of(tiers: tuple[FeeTierRow, ...]) -> PerformanceFeeSchedule | None:
    """Build the domain schedule from flat bands, or ``None`` when none were supplied.

    Raises the domain's own validation errors (gap, overlap, missing open end), so
    callers wrap it in :func:`translate_domain_errors` like any other value object.
    """
    if not tiers:
        return None
    return PerformanceFeeSchedule.of((tier.min_participants, tier.max_participants, tier.amount) for tier in tiers)


class ConnectOrganizationHandler:
    """Use case: connect a new organization and invite its first owner.

    Two facts in one transaction, because half of it is useless: an organization
    nobody can administer, or an invitation into an organization that does not
    exist. The invitation is issued directly rather than through the staff-invite
    use case — that one requires the inviter to be staff of the organization, and
    the platform administrator deliberately is not.

    The slug is the URL identity, so a collision is refused up front rather than
    left to the database constraint.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        invitations: StaffInvitationRepository,
        entitlements: ModuleEntitlementRepository,
        clock: Clock,
        uuids: UuidGenerator,
        hasher: TokenHasher,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._invitations = invitations
        self._entitlements = entitlements
        self._clock = clock
        self._uuids = uuids
        self._hasher = hasher
        self._events = events


    def _grant_modules(self, organization_id: OrganizationId, requested: tuple[str, ...] | None, *, now: datetime) -> list[DomainEvent]:
        """Write the organization's opening switchboard and return the events it produced.

        Every module gets a row, held or not, so the operator's console opens on a set
        of decisions rather than a blank. ``None`` means the full-access preset, which
        is what "connected to the platform" meant before the platform was sold in parts.
        """
        with translate_domain_errors():
            wanted = frozenset(OrganizationModule) if requested is None else frozenset(OrganizationModule.parse(name) for name in requested)

        produced: list[DomainEvent] = []
        for module in OrganizationModule:
            if module in wanted:
                entitlement, events = ModuleEntitlement.grant(
                    entitlement_id=ModuleEntitlementId.from_uuid(self._uuids.new()),
                    organization_id=organization_id,
                    module=module,
                    granted_by=None,
                    now=now,
                )
                produced.extend(events)
            else:
                entitlement = ModuleEntitlement.withheld(
                    entitlement_id=ModuleEntitlementId.from_uuid(self._uuids.new()),
                    organization_id=organization_id,
                    module=module,
                    now=now,
                )
            self._entitlements.save(entitlement)
        return produced

    def handle(self, command: ConnectOrganizationCommand) -> ConnectedOrganizationDto:
        now = self._clock.utcnow()

        with translate_domain_errors():
            name = OrganizationName(command.name)
            slug = OrganizationSlug(command.slug)
            commission = CommissionRate.of(command.commission_percent)
            fee_schedule = _schedule_of(command.fee_tiers)
            owner_email = StaffEmail(command.owner_email)
            connected_by = StaffUserId.from_string(command.connected_by)

        if self._organizations.find_by_slug(slug.value) is not None:
            raise OrganizationConflictError(f"Организация с адресом «{slug.value}» уже подключена.")

        organization, connected_events = Organization.connect(
            organization_id=OrganizationId.from_uuid(self._uuids.new()),
            name=name,
            slug=slug,
            commission_rate=commission,
            fee_schedule=fee_schedule,
            now=now,
        )
        self._organizations.save(organization)

        module_events = self._grant_modules(organization.id, command.modules, now=now)

        issued_token = self._hasher.generate()
        invitation, invitation_events = StaffInvitation.issue(
            invitation_id=StaffInvitationId.from_uuid(self._uuids.new()),
            organization_id=organization.id,
            email=owner_email,
            role=StaffRole.OWNER,
            token_hash=issued_token.token_hash,
            raw_token=issued_token.raw_token,
            invited_by=connected_by,
            policy=InvitationExpiryPolicy(),
            now=now,
        )
        self._invitations.save(invitation)

        # Published together: the invitation event is what sends the email, and it
        # must not go out before the organization it points at is stored.
        self._events.publish([*connected_events, *module_events, *invitation_events])
        return ConnectedOrganizationDto(
            organization=OrganizationSummaryView.from_organization(organization),
            owner_invitation=InvitationView.from_invitation(invitation),
        )


class SetCommissionRateHandler:
    """Use case: set an organization's commission rate.

    Changing the rate to what it already is returns quietly without a new event —
    re-saving a form is not a renegotiation.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._clock = clock
        self._events = events

    def handle(self, command: SetCommissionRateCommand) -> OrganizationSummaryView:
        with translate_domain_errors():
            organization_id = OrganizationId.from_string(command.organization_id)
            rate = CommissionRate.of(command.commission_percent)

        organization = self._organizations.get(organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Организация не найдена.")

        events = organization.change_commission_rate(rate, now=self._clock.utcnow())
        if events:
            self._organizations.save(organization)
            self._events.publish(events)
        return OrganizationSummaryView.from_organization(organization)


class SetPerformanceFeeScheduleHandler:
    """Use case: bill an organization a flat fee per performance.

    The other half of :class:`SetCommissionRateHandler`: the two use cases are the
    two commercial terms, and calling either is what puts the organization on that
    model. Submitting the schedule it already runs on returns quietly.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._clock = clock
        self._events = events

    def handle(self, command: SetPerformanceFeeScheduleCommand) -> OrganizationSummaryView:
        with translate_domain_errors():
            organization_id = OrganizationId.from_string(command.organization_id)
            schedule = _schedule_of(command.tiers)

        if schedule is None:
            raise InvalidInputError("Добавьте хотя бы один диапазон стоимости за выступление.")

        organization = self._organizations.get(organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Организация не найдена.")

        events = organization.change_fee_schedule(schedule, now=self._clock.utcnow())
        if events:
            self._organizations.save(organization)
            self._events.publish(events)
        return OrganizationSummaryView.from_organization(organization)


class ChangeOrganizationStatusHandler:
    """Use case: suspend a connected organization, or reactivate a suspended one.

    The platform's lever when an organization stops holding up its end: suspending
    it stops its staff editing anything, without deleting a festival's history.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._clock = clock
        self._events = events

    def handle(self, command: ChangeOrganizationStatusCommand) -> OrganizationSummaryView:
        with translate_domain_errors():
            organization_id = OrganizationId.from_string(command.organization_id)
            status = OrganizationStatus(command.status)

        organization = self._organizations.get(organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Организация не найдена.")

        now = self._clock.utcnow()
        with translate_domain_errors():
            events = organization.suspend(now=now) if status is OrganizationStatus.SUSPENDED else organization.reactivate(now=now)

        self._organizations.save(organization)
        self._events.publish(events)
        return OrganizationSummaryView.from_organization(organization)


class ListOrganizationsHandler:
    """Use case: every connected organization, as the platform operator sees them."""

    def __init__(self, *, organizations: OrganizationRepository) -> None:
        self._organizations = organizations

    def handle(self) -> list[OrganizationSummaryView]:
        return [OrganizationSummaryView.from_organization(org) for org in self._organizations.list_all()]
