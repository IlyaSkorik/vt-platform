"""The platform operator's cross-organization read model.

What the operator's console is for: how much work is sitting in each state across
*every* connected organization, what the participation fees behind it come to, and
what share of those fees is owed to the platform.

This reads the Competitions and Applications tables directly rather than through
each context's ports. That is the same pragmatic seam the organizer workspace
already uses (``apps.applications.presentation.api.v1.organizer``): a reporting
projection over data several contexts own, kept in the presentation layer where
its coupling is visible, rather than smuggled into a domain that would then have
to know about all of them.

What the platform is owed is computed the way that organization is billed — a
share of its fees, or a flat price per performance banded by how many participants
that performance has. The second one is why this projection also reads submissions:
a per-performance fee cannot be read off an order total, only off the headcount of
each performance in it.

The other side of the books is read here too. Commission is income; what the
platform *spent* is recorded by hand in the Finance context, and the difference is
the only figure that answers "are we ahead or behind?". It is reported twice,
because the two questions behind it are different ones: against the commission
that has actually been paid, and against the commission expected once every
outstanding order settles.

Expenses are recorded against an organization or against nobody, never against a
festival. A dashboard narrowed to one competition therefore has no honest expense
figure to show, and says so through ``expenses_apply`` rather than subtracting an
organization-wide cost from one festival's commission.

Money is summed as :class:`~decimal.Decimal` and never as a float: these are
figures the operator invoices against.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.applications.infrastructure.models import ApplicationModel, SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.finance.infrastructure.models import PlatformExpenseModel
from apps.organization.domain.value_objects import BillingModel, CommissionRate, PerformanceFeeSchedule, PerformanceFeeTier
from apps.organization.infrastructure.mappers.organization_mapper import fee_schedule_from_json
from apps.organization.infrastructure.models import OrganizationModel

__all__ = ["CompetitionOption", "DashboardView", "OrganizationBreakdown", "build_dashboard"]

#: The order the operator reads statuses in — the order of the funnel itself, so
#: the console shows a pipeline rather than an alphabetical list.
APPLICATION_STATUSES: tuple[str, ...] = ("DRAFT", "SUBMITTED", "WAITING_PAYMENT", "PAID", "COMPLETED", "CANCELLED")

#: Orders that never became revenue: a draft was never placed, a cancellation was
#: called off. Everything else is a fee somebody is expected to pay, or has.
_UNBILLABLE_STATUSES = frozenset({"DRAFT", "CANCELLED"})

#: Orders whose money has actually arrived, as far as the platform can tell.
_SETTLED_STATUSES = frozenset({"PAID", "COMPLETED"})


def _amount(total_price: object) -> Decimal:
    """The order's total as a decimal, or zero when it has no priced lines yet.

    The snapshot is written by ``ApplicationMapper._total_to_json`` under ``total``
    — the order's grand total, submissions plus services. ``amount`` is accepted as
    well because that is the key a single ``Money`` is written under elsewhere in
    the same column family, and reading a total as zero is a silent wrong number.
    """
    if not isinstance(total_price, dict):
        return Decimal("0")
    raw = total_price.get("total")
    if raw is None:
        raw = total_price.get("amount")
    try:
        return Decimal(str(raw or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _participant_counts(competition_ids: list[uuid.UUID]) -> dict[str, int]:
    """How many participants each performance in scope has, keyed by submission id.

    The headcount is the sum of the participants\' ``member_count``, so a collective
    entry counts the people it brings rather than one — the same figure the
    Submission aggregate exposes, read straight off the JSON column because this is
    a projection and loading every aggregate to count would be absurd.
    """
    counts: dict[str, int] = {}
    rows = SubmissionModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "participants")
    for row in rows:
        participants = row["participants"] if isinstance(row["participants"], list) else []
        total = 0
        for participant in participants:
            if not isinstance(participant, dict):
                continue
            try:
                total += int(participant.get("member_count", 1) or 1)
            except (TypeError, ValueError):
                total += 1
        counts[str(row["id"])] = total
    return counts


def _performance_fee(refs: object, schedule: PerformanceFeeSchedule, counts: dict[str, int]) -> Decimal:
    """What the platform is owed for one order under a per-performance schedule.

    One band price per performance the order holds. A performance whose headcount is
    unknown (a submission deleted from under a stale reference) is priced as a solo
    rather than skipped: the order did include it.
    """
    if not isinstance(refs, list):
        return Decimal("0.00")
    fee = Decimal("0.00")
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        fee += schedule.fee_for(counts.get(str(ref.get("submission_id")), 1))
    return fee


def _expense_totals(organization_filter: str | None) -> tuple[dict[uuid.UUID, Decimal], Decimal]:
    """What the platform spent, summed per organization plus its own overheads.

    Costs carried for a client come back keyed by that client; costs the platform
    carried itself come back as the second value, because they belong to the
    platform total and to nobody's line. Narrowing to one organization drops them:
    a server bill is not part of whether that client is profitable.

    Summed in the database rather than row by row — this is a projection, and the
    ledger is the one table here that grows with the operator's bookkeeping rather
    than with the festivals.
    """
    rows = PlatformExpenseModel.objects.filter(deleted_at__isnull=True)
    if organization_filter:
        rows = rows.filter(organization_id=organization_filter)
    per_organization: dict[uuid.UUID, Decimal] = {}
    unattributed = Decimal("0.00")
    for organization_id, amount in rows.values_list("organization_id", "amount"):
        value = Decimal(str(amount))
        if organization_id is None:
            unattributed += value
            continue
        per_organization[organization_id] = per_organization.get(organization_id, Decimal("0.00")) + value
    return per_organization, unattributed


@dataclass(slots=True)
class _Totals:
    """The running figures for one bucket (an organization, or the whole platform)."""

    status_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(APPLICATION_STATUSES, 0))
    applications: int = 0
    expected_fees: Decimal = Decimal("0")
    settled_fees: Decimal = Decimal("0")
    #: The per-performance fee behind the same orders. Accumulated per order rather
    #: than derived from the totals above, because it does not come from them.
    expected_performance_fee: Decimal = Decimal("0")
    settled_performance_fee: Decimal = Decimal("0")

    def add(self, status: str, amount: Decimal, performance_fee: Decimal = Decimal("0")) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1
        self.applications += 1
        if status not in _UNBILLABLE_STATUSES:
            self.expected_fees += amount
            self.expected_performance_fee += performance_fee
        if status in _SETTLED_STATUSES:
            self.settled_fees += amount
            self.settled_performance_fee += performance_fee


@dataclass(frozen=True, slots=True)
class OrganizationBreakdown:
    """One organization's line in the operator's dashboard."""

    organization_id: str | None
    name: str
    status: str
    billing_model: str
    commission_percent: Decimal
    fee_tiers: tuple[PerformanceFeeTier, ...]
    competitions: int
    applications: int
    status_counts: dict[str, int]
    expected_fees: Decimal
    settled_fees: Decimal
    expected_commission: Decimal
    settled_commission: Decimal
    #: Costs recorded against this organization. Zero is the ordinary state — most
    #: organizations cost the platform nothing beyond the overheads nobody attributes.
    expenses: Decimal
    #: Commission actually paid, less those costs. Negative means this organization
    #: has cost the platform more than it has yet brought in.
    profit: Decimal
    #: The same subtraction against commission still expected — what the line comes
    #: to once every outstanding order settles.
    potential_profit: Decimal


@dataclass(frozen=True, slots=True)
class CompetitionOption:
    """A competition the operator can filter the dashboard down to."""

    id: str
    title: str
    organization_id: str | None
    organization_name: str


@dataclass(frozen=True, slots=True)
class DashboardView:
    """The whole console read model: platform totals plus a line per organization."""

    status_counts: dict[str, int]
    applications: int
    expected_fees: Decimal
    settled_fees: Decimal
    expected_commission: Decimal
    settled_commission: Decimal
    #: Every recorded cost in scope, attributed and not.
    expenses: Decimal
    #: The part of it carried for no particular client — hosting, an accountant, an
    #: advertisement for the platform. Named separately because it is the figure
    #: that explains why the organizations' lines do not add up to the total.
    unattributed_expenses: Decimal
    profit: Decimal
    potential_profit: Decimal
    #: False when a competition filter is on. Expenses are recorded per organization
    #: and never per festival, so the figures above are zeroed rather than guessed at,
    #: and the console hides the profit block instead of showing a number it invented.
    expenses_apply: bool
    organizations: list[OrganizationBreakdown]
    competitions: list[CompetitionOption]


def _competition_scope(
    *,
    organization_filter: str | None,
    competition_filter: str | None,
) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, str], dict[uuid.UUID, int]]:
    """Map competitions to their owning organization, with titles and per-org counts."""
    rows = CompetitionModel.objects.filter(deleted_at__isnull=True).values("id", "title", "organizer_id")
    owner_of: dict[uuid.UUID, uuid.UUID] = {}
    titles: dict[uuid.UUID, str] = {}
    per_organization: dict[uuid.UUID, int] = {}
    for row in rows:
        competition_id = row["id"]
        organizer_id = row["organizer_id"]
        if organization_filter and str(organizer_id) != organization_filter:
            continue
        if competition_filter and str(competition_id) != competition_filter:
            continue
        owner_of[competition_id] = organizer_id
        titles[competition_id] = str(row["title"])
        per_organization[organizer_id] = per_organization.get(organizer_id, 0) + 1
    return owner_of, titles, per_organization


def build_dashboard(*, organization_id: str | None = None, competition_id: str | None = None) -> DashboardView:
    """Aggregate applications across every organization, optionally filtered.

    ``organization_id`` narrows to one organization, ``competition_id`` to one
    festival; passing both narrows to their intersection. The competition list is
    always the *unfiltered* one for the chosen organization, because it is what the
    console's filter control is built from.
    """
    organizations = list(OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at"))
    organization_names = {org.id: org.name for org in organizations}

    owner_of, _titles, competitions_per_organization = _competition_scope(
        organization_filter=organization_id,
        competition_filter=competition_id,
    )

    # Every stored price list, and separately the organizations actually billed off
    # one. A schedule outlives a switch back to the percentage model (the terms last
    # agreed are remembered), so the two are not the same set — and only the second
    # one needs the extra reads below, so an installation where nobody is on that
    # model pays for nothing.
    schedules: dict[uuid.UUID, PerformanceFeeSchedule] = {}
    fee_billed: set[uuid.UUID] = set()
    for org in organizations:
        schedule = fee_schedule_from_json(org.performance_fee_tiers)
        if schedule is None:
            continue
        schedules[org.id] = schedule
        if org.billing_model == BillingModel.PER_PERFORMANCE_FEE:
            fee_billed.add(org.id)

    per_organization: dict[uuid.UUID | None, _Totals] = {}
    platform = _Totals()
    columns = ["competition_id", "status", "total_price"]
    if fee_billed:
        columns.append("submission_refs")
    application_rows = ApplicationModel.objects.filter(
        deleted_at__isnull=True,
        competition_id__in=list(owner_of),
    ).values(*columns)
    participant_counts = _participant_counts(list(owner_of)) if fee_billed else {}
    for row in application_rows:
        organizer_id = owner_of.get(row["competition_id"])
        bucket = per_organization.setdefault(organizer_id, _Totals())
        amount = _amount(row["total_price"])
        schedule = schedules.get(organizer_id) if organizer_id in fee_billed else None
        fee = Decimal("0.00") if schedule is None else _performance_fee(row.get("submission_refs"), schedule, participant_counts)
        bucket.add(str(row["status"]), amount, fee)
        platform.add(str(row["status"]), amount, fee)

    # The expense side. Skipped entirely when a competition filter is on: costs are
    # recorded against an organization or against nobody, so there is no honest way
    # to narrow them to one festival, and a profit figure computed from the wrong
    # denominator is worse than no profit figure.
    expenses_apply = not competition_id
    expenses_of, unattributed_expenses = _expense_totals(organization_id) if expenses_apply else ({}, Decimal("0.00"))

    breakdowns: list[OrganizationBreakdown] = []
    expected_commission_total = Decimal("0")
    settled_commission_total = Decimal("0")
    for org in organizations:
        if organization_id and str(org.id) != organization_id:
            continue
        totals = per_organization.get(org.id, _Totals())
        schedule = schedules.get(org.id)
        if org.id in fee_billed:
            # Billed per performance: the figure was accumulated order by order above,
            # and the organization\'s percentage rate says nothing about what it owes.
            expected_commission = totals.expected_performance_fee
            settled_commission = totals.settled_performance_fee
        else:
            rate = CommissionRate(org.commission_percent)
            expected_commission = rate.apply_to(totals.expected_fees)
            settled_commission = rate.apply_to(totals.settled_fees)
        expected_commission_total += expected_commission
        settled_commission_total += settled_commission
        expenses = expenses_of.get(org.id, Decimal("0.00"))
        breakdowns.append(
            OrganizationBreakdown(
                organization_id=str(org.id),
                name=org.name,
                status=org.status,
                billing_model=str(org.billing_model),
                commission_percent=org.commission_percent,
                # Reported whether or not it is what the organization is billed off:
                # the console shows both terms and lets `billingModel` say which is live.
                fee_tiers=() if schedule is None else schedule.tiers,
                competitions=competitions_per_organization.get(org.id, 0),
                applications=totals.applications,
                status_counts=totals.status_counts,
                expected_fees=totals.expected_fees,
                settled_fees=totals.settled_fees,
                expected_commission=expected_commission,
                settled_commission=settled_commission,
                expenses=expenses,
                profit=settled_commission - expenses,
                potential_profit=expected_commission - expenses,
            )
        )

    # Competitions whose organizer id matches no connected organization — data from
    # before organizations were a thing the platform tracked. Reported rather than
    # dropped: their applications are real, and silently omitting them would make
    # the platform total disagree with the organizations' lines.
    orphan_ids = {organizer for organizer in owner_of.values() if organizer not in organization_names}
    if orphan_ids and not organization_id:
        orphan = _Totals()
        for organizer_id in orphan_ids:
            # A distinct name: `totals` is already bound as a non-optional `_Totals`
            # elsewhere in this function, so reusing it hid the `None` this can return.
            orphan_totals = per_organization.get(organizer_id)
            if orphan_totals is None:
                continue
            for status, count in orphan_totals.status_counts.items():
                orphan.status_counts[status] = orphan.status_counts.get(status, 0) + count
            orphan.applications += orphan_totals.applications
            orphan.expected_fees += orphan_totals.expected_fees
            orphan.settled_fees += orphan_totals.settled_fees
        if orphan.applications or any(competitions_per_organization.get(o, 0) for o in orphan_ids):
            breakdowns.append(
                OrganizationBreakdown(
                    organization_id=None,
                    name="Без организации",
                    status="ACTIVE",
                    billing_model=BillingModel.COMMISSION_PERCENT.value,
                    commission_percent=Decimal("0.00"),
                    fee_tiers=(),
                    competitions=sum(competitions_per_organization.get(o, 0) for o in orphan_ids),
                    applications=orphan.applications,
                    status_counts=orphan.status_counts,
                    expected_fees=orphan.expected_fees,
                    settled_fees=orphan.settled_fees,
                    expected_commission=Decimal("0.00"),
                    settled_commission=Decimal("0.00"),
                    # Nothing can be spent against an organizer the platform does not
                    # have on its books: the console only ever offers connected ones.
                    expenses=Decimal("0.00"),
                    profit=Decimal("0.00"),
                    potential_profit=Decimal("0.00"),
                )
            )

    options_owner_of, options_titles, _ = _competition_scope(organization_filter=organization_id, competition_filter=None)
    competitions = [
        CompetitionOption(
            id=str(competition),
            title=options_titles[competition],
            organization_id=str(owner) if owner in organization_names else None,
            organization_name=organization_names.get(owner, "Без организации"),
        )
        for competition, owner in options_owner_of.items()
    ]
    competitions.sort(key=lambda option: option.title.lower())

    # The platform total is every cost in scope, attributed or not — which is why it
    # is summed here rather than added up from the organizations' lines, where the
    # overheads belonging to nobody would have nowhere to appear.
    expenses_total = sum(expenses_of.values(), Decimal("0.00")) + unattributed_expenses

    return DashboardView(
        status_counts=platform.status_counts,
        applications=platform.applications,
        expected_fees=platform.expected_fees,
        settled_fees=platform.settled_fees,
        expected_commission=expected_commission_total,
        settled_commission=settled_commission_total,
        expenses=expenses_total,
        unattributed_expenses=unattributed_expenses,
        profit=settled_commission_total - expenses_total,
        potential_profit=expected_commission_total - expenses_total,
        expenses_apply=expenses_apply,
        organizations=breakdowns,
        competitions=competitions,
    )
