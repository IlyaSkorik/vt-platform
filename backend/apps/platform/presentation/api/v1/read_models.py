"""The platform operator's cross-organization read model.

What the operator's console is for: how much work is sitting in each state across
*every* connected organization, what the platform is owed for it, how much of that
has actually been paid, and what is left over once the platform's own costs come
off.

This reads the Competitions and Applications tables directly rather than through
each context's ports. That is the same pragmatic seam the organizer workspace
already uses (``apps.applications.presentation.api.v1.organizer``): a reporting
projection over data several contexts own, kept in the presentation layer where
its coupling is visible, rather than smuggled into a domain that would then have
to know about all of them.

**The unit the platform bills is the performance, not the order.** An order is a
basket — it can hold five entries, be half cancelled, and carry additional
services the organizer sells and the platform has no share of. What the platform
is owed is decided entry by entry, so this projection counts entries and never
order totals. Under :attr:`BillingModel.PER_PERFORMANCE_FEE` the price comes off
the organization's fee schedule, banded by how many participants the entry has;
under :attr:`BillingModel.COMMISSION_PERCENT` it is a share of what the entries
themselves cost, with the order's additional services deliberately outside the
base.

**An entry is billable from ``ACCEPTED`` on** — see
:data:`BILLABLE_SUBMISSION_STATUSES`. That is the same line the Diplomas and
Programs contexts draw, and it is drawn here again rather than imported, because
the three must stay free to disagree.

**Accrued is not received.** What an organization owes is derived; whether the
money arrived is a fact only a bank statement carries, and it is entered by hand
in the Finance context. The console reports both and their difference, because
"who still owes us?" is unanswerable from either figure alone.

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
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.applications.infrastructure.models import ApplicationModel, SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.finance.infrastructure.models import CommissionPaymentModel, PlatformExpenseModel
from apps.organization.domain.value_objects import BillingModel, CommissionRate, PerformanceFeeSchedule, PerformanceFeeTier
from apps.organization.infrastructure.mappers.organization_mapper import fee_schedule_from_json
from apps.organization.infrastructure.models import OrganizationModel

__all__ = [
    "APPLICATION_STATUSES",
    "BILLABLE_SUBMISSION_STATUSES",
    "CompetitionOption",
    "DashboardView",
    "FeeTierBreakdown",
    "OrganizationBreakdown",
    "build_dashboard",
]

#: The order the operator reads statuses in — the order of the funnel itself, so
#: the console shows a pipeline rather than an alphabetical list.
APPLICATION_STATUSES: tuple[str, ...] = ("DRAFT", "SUBMITTED", "WAITING_PAYMENT", "PAID", "COMPLETED", "CANCELLED")

#: The entry statuses the platform is owed for: committed to taking part.
#:
#: From ``ACCEPTED`` the applicant can no longer withdraw, the fee is settled and
#: the entry is in the competition; ``SCHEDULED`` adds a slot in the running order
#: and ``COMPLETED`` means it happened. Everything earlier is a decision not yet
#: made, and ``CANCELLED`` is one made the other way — a cancelled entry gets no
#: diploma and is billed for nothing.
#:
#: Read off the *current* status and not off the history on purpose. An entry the
#: organizer later cancelled is not work the platform delivered, so it drops out of
#: the figures rather than leaving a charge behind it.
BILLABLE_SUBMISSION_STATUSES: frozenset[str] = frozenset({"ACCEPTED", "SCHEDULED", "COMPLETED"})

#: Which transition dates an entry's billing date is read from, best first.
#:
#: ``PAID`` is the honest answer where a participant really paid: the order-level
#: payment path stamps it when the receipt is accepted. The organizer's "Одобрить"
#: button runs the whole tail in one request, so there it is the approval date
#: instead — still the day the entry became chargeable, which is what a period
#: report needs. ``ACCEPTED`` is the fallback for an entry that reached the
#: competition by some path that left no ``PAID`` stamp at all.
_BILLING_DATE_STATUSES: tuple[str, ...] = ("PAID", "ACCEPTED")


def _amount(total_price: object) -> Decimal:
    """The order's total as a decimal, or zero when it has no priced lines yet.

    The snapshot is written by ``ApplicationMapper._total_to_json`` under ``total``
    — the order's grand total, submissions plus services. ``amount`` is accepted as
    well because that is the key a single ``Money`` is written under elsewhere in
    the same column family, and reading a total as zero is a silent wrong number.

    Used for the funnel's "что люди заплатили организатору" figure only. The
    commission base is built from the entries themselves — see
    :func:`_billable_performances`.
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


def _headcount(participants: object) -> int:
    """How many people one entry puts on stage.

    The sum of the participants' ``member_count``, so a collective entry counts the
    people it brings rather than one — the same figure the Submission aggregate
    exposes, read straight off the JSON column because this is a projection and
    loading every aggregate to count would be absurd.

    A row that states no number is one performer, which is the honest reading of an
    entry filled in before the field existed. An entry with no participants at all
    is still one performance and prices as a solo: the fee schedule starts at one.
    """
    rows = participants if isinstance(participants, list) else []
    total = 0
    for participant in rows:
        if not isinstance(participant, dict):
            continue
        try:
            total += int(participant.get("member_count", 1) or 1)
        except (TypeError, ValueError):
            total += 1
    return max(total, 1)


def _entry_fee(price_snapshot: object) -> Decimal:
    """What the participant was charged for this one entry.

    Written by ``SubmissionMapper._price_to_json`` under ``amount``. Zero when the
    entry never had a price computed — which is possible for an entry an organizer
    walked through by hand, and is reported as zero rather than guessed at.
    """
    if not isinstance(price_snapshot, dict):
        return Decimal("0.00")
    try:
        return Decimal(str(price_snapshot.get("amount") or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _billing_date(status_history: object) -> date | None:
    """The day this entry became chargeable, or ``None`` when its history says nothing.

    The *earliest* transition into the best available status, not the latest: an
    entry that was marked paid, returned and paid again is chargeable from the first
    time, which is the month it belongs to on an invoice.

    ``None`` is possible only for an entry whose history is missing or unreadable.
    Such an entry is kept in the untimed figures and dropped by a period filter —
    see :func:`_billable_performances`.
    """
    rows = status_history if isinstance(status_history, list) else []
    found: dict[str, date] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("to_status") or "")
        if status not in _BILLING_DATE_STATUSES:
            continue
        raw = row.get("occurred_at")
        if not isinstance(raw, str):
            continue
        try:
            occurred = datetime.fromisoformat(raw).date()
        except ValueError:
            continue
        previous = found.get(status)
        if previous is None or occurred < previous:
            found[status] = occurred
    for status in _BILLING_DATE_STATUSES:
        if status in found:
            return found[status]
    return None


@dataclass(frozen=True, slots=True)
class _Performance:
    """One billable entry, reduced to the four facts the money depends on."""

    organization_id: uuid.UUID | None
    #: People on stage — what a fee schedule bands by.
    headcount: int
    #: What the participant was charged for it — the base a percentage applies to.
    fee: Decimal
    billed_on: date | None


def _billable_performances(
    competition_ids: list[uuid.UUID],
    owner_of: dict[uuid.UUID, uuid.UUID],
    *,
    since: date | None,
    until: date | None,
) -> list[_Performance]:
    """Every entry in scope the platform is owed for, narrowed to the period.

    An entry whose history carries no usable date is dropped as soon as *either*
    bound is set. Keeping it would put an undated charge into a month's act, which
    is worse than a figure the operator can see is missing: with no filter on, the
    same entry is counted, so nothing disappears from the untimed totals.
    """
    rows = SubmissionModel.objects.filter(
        deleted_at__isnull=True,
        competition_id__in=competition_ids,
        status__in=sorted(BILLABLE_SUBMISSION_STATUSES),
    ).values("competition_id", "participants", "price_snapshot", "status_history")

    performances: list[_Performance] = []
    for row in rows:
        billed_on = _billing_date(row["status_history"])
        if (since is not None or until is not None) and billed_on is None:
            continue
        if since is not None and billed_on is not None and billed_on < since:
            continue
        if until is not None and billed_on is not None and billed_on > until:
            continue
        performances.append(
            _Performance(
                organization_id=owner_of.get(row["competition_id"]),
                headcount=_headcount(row["participants"]),
                fee=_entry_fee(row["price_snapshot"]),
                billed_on=billed_on,
            )
        )
    return performances


def _expense_totals(
    organization_filter: str | None,
    *,
    since: date | None,
    until: date | None,
) -> tuple[dict[uuid.UUID, Decimal], Decimal]:
    """What the platform spent, summed per organization plus its own overheads.

    Costs carried for a client come back keyed by that client; costs the platform
    carried itself come back as the second value, because they belong to the
    platform total and to nobody's line. Narrowing to one organization drops them:
    a server bill is not part of whether that client is profitable.

    ``since``/``until`` read against ``spent_at`` — the day the money went, as the
    invoice says — so a period's profit is that period's income less that period's
    costs.
    """
    rows = PlatformExpenseModel.objects.filter(deleted_at__isnull=True)
    if organization_filter:
        rows = rows.filter(organization_id=organization_filter)
    if since is not None:
        rows = rows.filter(spent_at__gte=since)
    if until is not None:
        rows = rows.filter(spent_at__lte=until)
    per_organization: dict[uuid.UUID, Decimal] = {}
    unattributed = Decimal("0.00")
    for organization_id, amount in rows.values_list("organization_id", "amount"):
        value = Decimal(str(amount))
        if organization_id is None:
            unattributed += value
            continue
        per_organization[organization_id] = per_organization.get(organization_id, Decimal("0.00")) + value
    return per_organization, unattributed


def _received_totals(
    organization_filter: str | None,
    *,
    since: date | None,
    until: date | None,
) -> dict[uuid.UUID, Decimal]:
    """What each organization actually paid the platform over the period.

    Read straight off the Finance table rather than through
    ``CommissionPaymentService``: this is a projection, it wants sums and not
    aggregates, and the service's own ``totals_by_organization`` exists for callers
    that need the use-case layer. Organizations that paid nothing are absent, which
    the caller reads as zero.
    """
    rows = CommissionPaymentModel.objects.filter(deleted_at__isnull=True)
    if organization_filter:
        rows = rows.filter(organization_id=organization_filter)
    if since is not None:
        rows = rows.filter(received_at__gte=since)
    if until is not None:
        rows = rows.filter(received_at__lte=until)
    totals: dict[uuid.UUID, Decimal] = {}
    for organization_id, amount in rows.values_list("organization_id", "amount"):
        totals[organization_id] = totals.get(organization_id, Decimal("0.00")) + Decimal(str(amount))
    return totals


@dataclass(slots=True)
class _Totals:
    """The running funnel figures for one bucket (an organization, or the platform).

    Orders only. The money moved out of here when the billing unit became the
    performance: what is left is the pipeline the operator reads to see how much
    work is in flight, plus what the participants paid the organizer for it.
    """

    status_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(APPLICATION_STATUSES, 0))
    applications: int = 0
    #: What participants were charged across the orders that are not drafts or
    #: cancellations. The organizer's revenue, not the platform's base — shown so
    #: the two are visibly different numbers.
    order_fees: Decimal = Decimal("0")

    def add(self, status: str, amount: Decimal) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1
        self.applications += 1
        if status not in {"DRAFT", "CANCELLED"}:
            self.order_fees += amount


@dataclass(slots=True)
class _Charges:
    """What one organization's billable entries come to, accumulated entry by entry."""

    performances: int = 0
    participants: int = 0
    #: The sum of the entries' own prices — the base a percentage is taken of.
    base: Decimal = Decimal("0.00")
    #: Headcounts seen, for the per-performance breakdown. Kept as a tally rather
    #: than a list: a festival has thousands of entries and at most a few dozen
    #: distinct headcounts.
    headcounts: dict[int, int] = field(default_factory=dict)

    def add(self, performance: _Performance) -> None:
        self.performances += 1
        self.participants += performance.headcount
        self.base += performance.fee
        self.headcounts[performance.headcount] = self.headcounts.get(performance.headcount, 0) + 1


@dataclass(frozen=True, slots=True)
class FeeTierBreakdown:
    """One band of a fee schedule, with what actually fell into it.

    The row an act is written from: *this many entries of this size, at this price,
    come to this much*. Reported for every band of the schedule including the ones
    nothing fell into — a price list with rows silently missing is one the organizer
    cannot check against their own copy.
    """

    min_participants: int
    max_participants: int | None
    #: The band as a human reads it: ``1``, ``2-5``, ``6+``.
    range_label: str
    #: What one entry in this band costs the organization.
    unit_amount: Decimal
    #: How many billable entries fell into it.
    performances: int
    #: ``unit_amount`` × ``performances``.
    amount: Decimal


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
    #: What participants paid the organizer across its orders. Context, not a base.
    order_fees: Decimal
    #: Billable entries in scope, and the people in them.
    performances: int
    participants: int
    #: The sum of those entries' own prices — what a percentage is taken of. Zero
    #: under the per-performance model, where the price list replaces it entirely.
    commission_base: Decimal
    #: What the organization owes for them, by whichever model it is billed under.
    accrued_commission: Decimal
    #: What it has actually paid, from the Finance receipts ledger.
    received_commission: Decimal
    #: The difference. Negative means it has overpaid — a prepayment, or a period
    #: filter that caught the payment and not the work it settled.
    commission_debt: Decimal
    #: Per-band rows behind ``accrued_commission``. Empty unless the organization is
    #: billed per performance, where it is the only honest way to show the figure.
    fee_breakdown: tuple[FeeTierBreakdown, ...]
    #: Costs recorded against this organization. Zero is the ordinary state — most
    #: organizations cost the platform nothing beyond the overheads nobody attributes.
    expenses: Decimal
    #: Money received, less those costs. Negative means this organization has cost
    #: the platform more than it has yet paid.
    profit: Decimal


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
    order_fees: Decimal
    performances: int
    participants: int
    commission_base: Decimal
    accrued_commission: Decimal
    received_commission: Decimal
    commission_debt: Decimal
    #: Every recorded cost in scope, attributed and not.
    expenses: Decimal
    #: The part of it carried for no particular client — hosting, an accountant, an
    #: advertisement for the platform. Named separately because it is the figure
    #: that explains why the organizations' lines do not add up to the total.
    unattributed_expenses: Decimal
    profit: Decimal
    #: False when a competition filter is on. Expenses are recorded per organization
    #: and never per festival, so the figures above are zeroed rather than guessed at,
    #: and the console hides the profit block instead of showing a number it invented.
    expenses_apply: bool
    #: True when a period filter is on. The money figures honour it; the funnel above
    #: them does not, because an order has no one date to file it under — it is told
    #: so it can say which half of the screen the dates apply to.
    period_applies: bool
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


def _fee_breakdown(schedule: PerformanceFeeSchedule, headcounts: dict[int, int]) -> tuple[tuple[FeeTierBreakdown, ...], Decimal]:
    """The schedule's bands with what fell into each, and what they come to together.

    The total is summed from the rows rather than computed separately, so the act's
    lines always add up to the figure beside them — the one arithmetic error an
    operator cannot be expected to catch is the one between a table and its total.
    """
    counts = dict.fromkeys(range(len(schedule.tiers)), 0)
    for headcount, occurrences in headcounts.items():
        for index, tier in enumerate(schedule.tiers):
            if tier.contains(headcount):
                counts[index] += occurrences
                break
        else:
            # Unreachable for a valid schedule (the bands cover 1..∞) and for a
            # headcount of at least one, which `_headcount` guarantees. Priced off
            # the first band rather than dropped, matching `PerformanceFeeSchedule.
            # fee_for`: a reporting projection must not lose an entry to a number it
            # did not expect.
            counts[0] += occurrences

    rows: list[FeeTierBreakdown] = []
    total = Decimal("0.00")
    for index, tier in enumerate(schedule.tiers):
        performances = counts[index]
        amount = tier.amount * performances
        total += amount
        rows.append(
            FeeTierBreakdown(
                min_participants=tier.min_participants,
                max_participants=tier.max_participants,
                range_label=tier.range_label(),
                unit_amount=tier.amount,
                performances=performances,
                amount=amount,
            )
        )
    return tuple(rows), total


def build_dashboard(
    *,
    organization_id: str | None = None,
    competition_id: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> DashboardView:
    """Aggregate the platform's books across every organization, optionally filtered.

    ``organization_id`` narrows to one organization, ``competition_id`` to one
    festival; passing both narrows to their intersection. ``since``/``until`` narrow
    the money to a period — billable entries by the day they became chargeable,
    expenses by the day they were spent, receipts by the day they landed — and
    deliberately leave the order funnel alone (see :attr:`DashboardView.period_applies`).

    The competition list is always the *unfiltered* one for the chosen organization,
    because it is what the console's filter control is built from.
    """
    organizations = list(OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at"))
    organization_names = {org.id: org.name for org in organizations}

    owner_of, _titles, competitions_per_organization = _competition_scope(
        organization_filter=organization_id,
        competition_filter=competition_id,
    )

    # Every stored price list, and separately the organizations actually billed off
    # one. A schedule outlives a switch back to the percentage model (the terms last
    # agreed are remembered), so the two are not the same set.
    schedules: dict[uuid.UUID, PerformanceFeeSchedule] = {}
    fee_billed: set[uuid.UUID] = set()
    for org in organizations:
        schedule = fee_schedule_from_json(org.performance_fee_tiers)
        if schedule is None:
            continue
        schedules[org.id] = schedule
        if org.billing_model == BillingModel.PER_PERFORMANCE_FEE:
            fee_billed.add(org.id)

    # The funnel: orders, by state. Kept whole-period — an order spans the weeks
    # between being drafted and being paid, and filing it under one date would make
    # every bucket but one wrong.
    per_organization: dict[uuid.UUID | None, _Totals] = {}
    platform = _Totals()
    application_rows = ApplicationModel.objects.filter(
        deleted_at__isnull=True,
        competition_id__in=list(owner_of),
    ).values("competition_id", "status", "total_price")
    for row in application_rows:
        organizer_id = owner_of.get(row["competition_id"])
        amount = _amount(row["total_price"])
        per_organization.setdefault(organizer_id, _Totals()).add(str(row["status"]), amount)
        platform.add(str(row["status"]), amount)

    # The money: entries, by what each one is worth.
    charges: dict[uuid.UUID | None, _Charges] = {}
    for performance in _billable_performances(list(owner_of), owner_of, since=since, until=until):
        charges.setdefault(performance.organization_id, _Charges()).add(performance)

    # The expense side. Skipped entirely when a competition filter is on: costs are
    # recorded against an organization or against nobody, so there is no honest way
    # to narrow them to one festival, and a profit figure computed from the wrong
    # denominator is worse than no profit figure.
    expenses_apply = not competition_id
    expenses_of, unattributed_expenses = _expense_totals(organization_id, since=since, until=until) if expenses_apply else ({}, Decimal("0.00"))
    # Receipts are narrowed the same way and for the same reason: an organization
    # pays its commission, not one festival's share of it.
    received_of = _received_totals(organization_id, since=since, until=until) if expenses_apply else {}

    breakdowns: list[OrganizationBreakdown] = []
    accrued_total = Decimal("0")
    received_total = Decimal("0")
    base_total = Decimal("0")
    performances_total = 0
    participants_total = 0
    for org in organizations:
        if organization_id and str(org.id) != organization_id:
            continue
        totals = per_organization.get(org.id, _Totals())
        charged = charges.get(org.id, _Charges())
        schedule = schedules.get(org.id)
        if org.id in fee_billed and schedule is not None:
            # Billed per performance: the price list decides, and the organization's
            # percentage rate says nothing about what it owes. The breakdown and the
            # figure come out of the same pass, so they cannot disagree.
            breakdown, accrued = _fee_breakdown(schedule, charged.headcounts)
            base = Decimal("0.00")
        else:
            breakdown = ()
            base = charged.base
            accrued = CommissionRate(org.commission_percent).apply_to(base)
        received = received_of.get(org.id, Decimal("0.00"))
        expenses = expenses_of.get(org.id, Decimal("0.00"))

        accrued_total += accrued
        received_total += received
        base_total += base
        performances_total += charged.performances
        participants_total += charged.participants

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
                order_fees=totals.order_fees,
                performances=charged.performances,
                participants=charged.participants,
                commission_base=base,
                accrued_commission=accrued,
                received_commission=received,
                commission_debt=accrued - received,
                fee_breakdown=breakdown,
                expenses=expenses,
                profit=received - expenses,
            )
        )

    # Competitions whose organizer id matches no connected organization — data from
    # before organizations were a thing the platform tracked. Reported rather than
    # dropped: their applications are real, and silently omitting them would make
    # the platform total disagree with the organizations' lines.
    orphan_ids = {organizer for organizer in owner_of.values() if organizer not in organization_names}
    if orphan_ids and not organization_id:
        orphan = _Totals()
        orphan_charges = _Charges()
        for organizer_id in orphan_ids:
            # Distinct names: `totals` and `charged` are already bound as
            # non-optional above, so reusing either hid the `None` these can return.
            orphan_totals = per_organization.get(organizer_id)
            if orphan_totals is not None:
                for status, count in orphan_totals.status_counts.items():
                    orphan.status_counts[status] = orphan.status_counts.get(status, 0) + count
                orphan.applications += orphan_totals.applications
                orphan.order_fees += orphan_totals.order_fees
            orphan_charged = charges.get(organizer_id)
            if orphan_charged is not None:
                orphan_charges.performances += orphan_charged.performances
                orphan_charges.participants += orphan_charged.participants
        if orphan.applications or any(competitions_per_organization.get(o, 0) for o in orphan_ids):
            performances_total += orphan_charges.performances
            participants_total += orphan_charges.participants
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
                    order_fees=orphan.order_fees,
                    performances=orphan_charges.performances,
                    participants=orphan_charges.participants,
                    # Nothing is owed on an organizer the platform has no terms with,
                    # and nothing can be spent or received against one either: the
                    # console only ever offers connected organizations.
                    commission_base=Decimal("0.00"),
                    accrued_commission=Decimal("0.00"),
                    received_commission=Decimal("0.00"),
                    commission_debt=Decimal("0.00"),
                    fee_breakdown=(),
                    expenses=Decimal("0.00"),
                    profit=Decimal("0.00"),
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
        order_fees=platform.order_fees,
        performances=performances_total,
        participants=participants_total,
        commission_base=base_total,
        accrued_commission=accrued_total,
        received_commission=received_total,
        commission_debt=accrued_total - received_total,
        expenses=expenses_total,
        unattributed_expenses=unattributed_expenses,
        profit=received_total - expenses_total,
        expenses_apply=expenses_apply,
        period_applies=since is not None or until is not None,
        organizations=breakdowns,
        competitions=competitions,
    )
