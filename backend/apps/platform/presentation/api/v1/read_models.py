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

Money is summed as :class:`~decimal.Decimal` and never as a float: these are
figures the operator invoices against.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.applications.infrastructure.models import ApplicationModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.organization.domain.value_objects import CommissionRate
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


@dataclass(slots=True)
class _Totals:
    """The running figures for one bucket (an organization, or the whole platform)."""

    status_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(APPLICATION_STATUSES, 0))
    applications: int = 0
    expected_fees: Decimal = Decimal("0")
    settled_fees: Decimal = Decimal("0")

    def add(self, status: str, amount: Decimal) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1
        self.applications += 1
        if status not in _UNBILLABLE_STATUSES:
            self.expected_fees += amount
        if status in _SETTLED_STATUSES:
            self.settled_fees += amount


@dataclass(frozen=True, slots=True)
class OrganizationBreakdown:
    """One organization's line in the operator's dashboard."""

    organization_id: str | None
    name: str
    status: str
    commission_percent: Decimal
    competitions: int
    applications: int
    status_counts: dict[str, int]
    expected_fees: Decimal
    settled_fees: Decimal
    expected_commission: Decimal
    settled_commission: Decimal


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

    per_organization: dict[uuid.UUID | None, _Totals] = {}
    platform = _Totals()
    application_rows = ApplicationModel.objects.filter(
        deleted_at__isnull=True,
        competition_id__in=list(owner_of),
    ).values("competition_id", "status", "total_price")
    for row in application_rows:
        organizer_id = owner_of.get(row["competition_id"])
        bucket = per_organization.setdefault(organizer_id, _Totals())
        amount = _amount(row["total_price"])
        bucket.add(str(row["status"]), amount)
        platform.add(str(row["status"]), amount)

    breakdowns: list[OrganizationBreakdown] = []
    expected_commission_total = Decimal("0")
    settled_commission_total = Decimal("0")
    for org in organizations:
        if organization_id and str(org.id) != organization_id:
            continue
        totals = per_organization.get(org.id, _Totals())
        rate = CommissionRate(org.commission_percent)
        expected_commission = rate.apply_to(totals.expected_fees)
        settled_commission = rate.apply_to(totals.settled_fees)
        expected_commission_total += expected_commission
        settled_commission_total += settled_commission
        breakdowns.append(
            OrganizationBreakdown(
                organization_id=str(org.id),
                name=org.name,
                status=org.status,
                commission_percent=org.commission_percent,
                competitions=competitions_per_organization.get(org.id, 0),
                applications=totals.applications,
                status_counts=totals.status_counts,
                expected_fees=totals.expected_fees,
                settled_fees=totals.settled_fees,
                expected_commission=expected_commission,
                settled_commission=settled_commission,
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
                    commission_percent=Decimal("0.00"),
                    competitions=sum(competitions_per_organization.get(o, 0) for o in orphan_ids),
                    applications=orphan.applications,
                    status_counts=orphan.status_counts,
                    expected_fees=orphan.expected_fees,
                    settled_fees=orphan.settled_fees,
                    expected_commission=Decimal("0.00"),
                    settled_commission=Decimal("0.00"),
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

    return DashboardView(
        status_counts=platform.status_counts,
        applications=platform.applications,
        expected_fees=platform.expected_fees,
        settled_fees=platform.settled_fees,
        expected_commission=expected_commission_total,
        settled_commission=settled_commission_total,
        organizations=breakdowns,
        competitions=competitions,
    )
