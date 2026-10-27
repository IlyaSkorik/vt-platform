"""Integration tests for the platform operator's console.

The console is what sits above every organization: connecting new ones, setting
what each owes the platform, and reading the pipeline across all of them. Access
comes only from the ``grant_platform_admin`` command, so these tests grant it the
same way the deployment would.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.applications.domain.value_objects import Currency, Money, TotalPriceSnapshot
from apps.applications.infrastructure.mappers.application_mapper import ApplicationMapper
from apps.applications.infrastructure.models import ApplicationModel, SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.infrastructure.models import UserModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel
from apps.participants.infrastructure.models import ParticipantRegistryModel
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler
from apps.teachers.infrastructure.models import TeacherModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ORGANIZATIONS = "/api/v1/platform/organizations"
_DASHBOARD = "/api/v1/platform/dashboard"
_AUDIENCE = "/api/v1/platform/audience"
_COMMISSION_PAYMENTS = "/api/v1/platform/commission-payments"


def _register(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Илья", "lastName": "Скорик"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return str(user_id)


@pytest.fixture
def operator() -> APIClient:
    """A client authenticated as the platform operator (granted by command)."""
    client = APIClient()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def organization_owner() -> APIClient:
    """A client authenticated as the OWNER of the platform's own organization."""
    client = APIClient()
    user_id = _register(client, "owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


#: The day the fixtures' entries become chargeable, unless a test says otherwise.
_BILLED_ON = date(2026, 3, 15)


def _total_price(amount: str) -> dict[str, str]:
    """The price snapshot exactly as ``ApplicationMapper._total_to_json`` writes it.

    Written out longhand rather than invented, because a fixture that invents its
    own key shape lets the console read zero forever while the suite stays green.
    """
    return {
        "total": amount,
        "submissions_total": amount,
        "services_total": "0.00",
        "currency": "BYN",
        "calculated_at": "2026-01-01T00:00:00+00:00",
    }


def _performance(
    *,
    competition_id: uuid.UUID,
    participants: int = 1,
    price: str = "0.00",
    status: str = "ACCEPTED",
    billed_on: date | None = _BILLED_ON,
) -> SubmissionModel:
    """One entry, written the way the Submission mapper writes one.

    This is the unit the platform bills, so the three facts the money reads off it
    are all written longhand: the headcount as one collective participant row
    carrying ``member_count``, the price under the key
    ``SubmissionMapper._price_to_json`` uses, and the transition into ``PAID`` the
    period filter reads as the day the entry became chargeable.

    ``billed_on=None`` leaves the history empty — an entry no period can place,
    which is its own case and is tested as one.
    """
    history: list[dict[str, object]] = []
    if billed_on is not None:
        stamped = datetime(billed_on.year, billed_on.month, billed_on.day, 12, tzinfo=UTC).isoformat()
        history = [
            {"from_status": "WAITING_PAYMENT", "to_status": "PAID", "occurred_at": stamped},
            {"from_status": "PAID", "to_status": "ACCEPTED", "occurred_at": stamped},
        ]
    return SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        participants=[{"id": str(uuid.uuid4()), "display_name": "Ансамбль", "member_count": participants, "members": []}],
        price_snapshot={"amount": price, "currency": "BYN", "calculated_at": "2026-01-01T00:00:00+00:00"},
        status_history=history,
    )


def _order(
    *,
    competition_id: uuid.UUID,
    status: str,
    amount: str | None,
) -> ApplicationModel:
    """One order. The funnel counts these; nothing about the commission reads them."""
    return ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        total_price=_total_price(amount) if amount is not None else None,
    )


#: The schedule from the operator's own example: a solo, a small group, the rest.
_TIERS = [
    {"minParticipants": 1, "maxParticipants": 1, "amount": "2.50"},
    {"minParticipants": 2, "maxParticipants": 5, "amount": "4.00"},
    {"minParticipants": 6, "maxParticipants": None, "amount": "6.00"},
]


class TestAccess:
    def test_an_anonymous_caller_is_refused(self) -> None:
        assert APIClient().get(_ORGANIZATIONS).status_code == 401

    def test_an_organization_owner_is_not_a_platform_operator(self, organization_owner: APIClient) -> None:
        # The whole point of the separation: the top of an organization is still
        # inside it, and the console that governs organizations is not theirs.
        assert organization_owner.get(_ORGANIZATIONS).status_code == 403
        assert organization_owner.get(_DASHBOARD).status_code == 403
        assert organization_owner.get(_AUDIENCE).status_code == 403

    def test_the_operator_is_admitted(self, operator: APIClient) -> None:
        assert operator.get(_ORGANIZATIONS).status_code == 200


class TestConnectingAnOrganization:
    def test_connects_and_emails_the_owner_an_invitation(self, operator: APIClient) -> None:
        mail.outbox.clear()

        response = operator.post(
            _ORGANIZATIONS,
            {"name": "Звёздный дождь", "ownerEmail": "director@example.com", "commissionPercent": "12.5"},
            format="json",
        )

        assert response.status_code == 201, response.data
        data = response.data["data"]
        assert data["name"] == "Звёздный дождь"
        assert data["slug"] == "zvezdnyy-dozhd"  # transliterated from the name
        assert data["commissionPercent"] == "12.50"
        assert data["status"] == "ACTIVE"

        assert OrganizationModel.objects.filter(name="Звёздный дождь").exists()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["director@example.com"]

    def test_refuses_a_second_organization_at_the_same_address(self, operator: APIClient) -> None:
        payload = {"name": "Звёздный дождь", "ownerEmail": "a@example.com", "commissionPercent": "5"}
        assert operator.post(_ORGANIZATIONS, payload, format="json").status_code == 201

        clash = operator.post(
            _ORGANIZATIONS,
            {"name": "Звёздный дождь", "ownerEmail": "b@example.com", "commissionPercent": "5"},
            format="json",
        )
        assert clash.status_code == 409

    def test_lists_the_connected_organizations(self, operator: APIClient) -> None:
        operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        )
        listed = operator.get(_ORGANIZATIONS)
        assert listed.status_code == 200
        names = [row["name"] for row in listed.data["data"]]
        assert "Гармония" in names


class TestCommercialTerms:
    def test_changes_the_commission_rate(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]

        updated = operator.patch(f"{_ORGANIZATIONS}/{created['id']}", {"commissionPercent": "15"}, format="json")

        assert updated.status_code == 200, updated.data
        assert updated.data["data"]["commissionPercent"] == "15.00"

    def test_connects_an_organization_on_the_per_performance_fee(self, operator: APIClient) -> None:
        response = operator.post(
            _ORGANIZATIONS,
            {
                "name": "Тарифный дом",
                "ownerEmail": "tariff@example.com",
                "billingModel": "PER_PERFORMANCE_FEE",
                "feeTiers": _TIERS,
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        data = response.data["data"]
        assert data["billingModel"] == "PER_PERFORMANCE_FEE"
        assert data["feeTiers"] == [
            {"minParticipants": 1, "maxParticipants": 1, "amount": "2.50"},
            {"minParticipants": 2, "maxParticipants": 5, "amount": "4.00"},
            {"minParticipants": 6, "maxParticipants": None, "amount": "6.00"},
        ]

        # And it survives the round trip through the JSON column, read back by the
        # roster rather than echoed from the aggregate that was just built.
        listed = operator.get(_ORGANIZATIONS).data["data"]
        stored = next(row for row in listed if row["id"] == data["id"])
        assert stored["feeTiers"] == data["feeTiers"]

    def test_switches_an_organization_between_the_two_models(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]
        url = f"{_ORGANIZATIONS}/{created['id']}"

        switched = operator.patch(url, {"billingModel": "PER_PERFORMANCE_FEE", "feeTiers": _TIERS}, format="json")
        assert switched.status_code == 200, switched.data
        assert switched.data["data"]["billingModel"] == "PER_PERFORMANCE_FEE"
        # The percentage last agreed is still there, ready if the operator switches back.
        assert switched.data["data"]["commissionPercent"] == "7.00"

        back = operator.patch(url, {"billingModel": "COMMISSION_PERCENT", "commissionPercent": "9"}, format="json")
        assert back.data["data"]["billingModel"] == "COMMISSION_PERCENT"
        assert back.data["data"]["commissionPercent"] == "9.00"
        # And the price list is remembered too, symmetrically — the console reads
        # `billingModel` to know which of the two terms is live.
        assert len(back.data["data"]["feeTiers"]) == 3

    def test_refuses_a_schedule_with_a_hole_in_it(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]

        gapped = operator.patch(
            f"{_ORGANIZATIONS}/{created['id']}",
            {
                "billingModel": "PER_PERFORMANCE_FEE",
                "feeTiers": [
                    {"minParticipants": 1, "maxParticipants": 1, "amount": "2.50"},
                    {"minParticipants": 3, "maxParticipants": None, "amount": "4.00"},
                ],
            },
            format="json",
        )

        assert gapped.status_code == 400, gapped.data

    def test_refuses_a_fee_model_without_any_bands(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]

        empty = operator.patch(
            f"{_ORGANIZATIONS}/{created['id']}",
            {"billingModel": "PER_PERFORMANCE_FEE", "feeTiers": []},
            format="json",
        )

        assert empty.status_code == 400, empty.data

    def test_suspends_and_reactivates(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]
        url = f"{_ORGANIZATIONS}/{created['id']}"

        assert operator.patch(url, {"status": "SUSPENDED"}, format="json").data["data"]["status"] == "SUSPENDED"
        assert operator.patch(url, {"status": "ACTIVE"}, format="json").data["data"]["status"] == "ACTIVE"

    def test_an_empty_patch_is_refused(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]
        assert operator.patch(f"{_ORGANIZATIONS}/{created['id']}", {}, format="json").status_code == 400


class TestDashboard:
    def _connected_with_a_festival(self, operator: APIClient, *, name: str, commission: str) -> tuple[str, CompetitionModel]:
        organization = operator.post(
            _ORGANIZATIONS,
            {"name": name, "ownerEmail": f"{uuid.uuid4().hex[:8]}@example.com", "commissionPercent": commission},
            format="json",
        ).data["data"]
        competition = CompetitionModel.objects.create(
            organizer_id=uuid.UUID(organization["id"]),
            status="PUBLISHED",
            title=f"{name} — сезон",
            season="2025/2026",
        )
        return organization["id"], competition

    def _on_the_fee_schedule(self, operator: APIClient) -> tuple[str, CompetitionModel]:
        """An organization billed per performance, with a festival to bill for."""
        organization = operator.post(
            _ORGANIZATIONS,
            {
                "name": "Тарифный дом",
                "ownerEmail": "tariff@example.com",
                "billingModel": "PER_PERFORMANCE_FEE",
                "feeTiers": _TIERS,
            },
            format="json",
        ).data["data"]
        competition = CompetitionModel.objects.create(
            organizer_id=uuid.UUID(organization["id"]),
            status="PUBLISHED",
            title="Тарифный дом — сезон",
            season="2025/2026",
        )
        return str(organization["id"]), competition

    def test_counts_applications_by_status_across_organizations(self, operator: APIClient) -> None:
        _, first = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, second = self._connected_with_a_festival(operator, name="Созвездие", commission="20")
        _order(competition_id=first.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=first.id, status="PAID", amount="200.00")
        _order(competition_id=second.id, status="CANCELLED", amount="500.00")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["statusCounts"]["SUBMITTED"] == 1
        assert data["statusCounts"]["PAID"] == 1
        assert data["statusCounts"]["CANCELLED"] == 1
        assert data["applications"] == 3

    def test_charges_a_percentage_of_the_entries_in_the_competition(self, operator: APIClient) -> None:
        # The base is the entries themselves, not the orders around them. An entry
        # still under review has not been delivered and is owed nothing for; one the
        # organizer cancelled is owed nothing for either, however far it got.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="100.00", status="ACCEPTED")
        _performance(competition_id=competition.id, price="200.00", status="COMPLETED")
        _performance(competition_id=competition.id, price="500.00", status="SUBMITTED")
        _performance(competition_id=competition.id, price="500.00", status="CANCELLED")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["performances"] == 2
        assert data["commissionBase"] == "300.00"
        assert data["accruedCommission"] == "30.00"
        # Nothing has been paid, so the whole accrual is still owed.
        assert data["receivedCommission"] == "0.00"
        assert data["commissionDebt"] == "30.00"

    def test_additional_services_are_outside_the_commission_base(self, operator: APIClient) -> None:
        # The order's total is entries plus whatever else the organizer sold. The
        # platform has no share of the second part, so the base must not move when
        # it changes — the bug this guards is a percentage quietly taken of a
        # photographer's fee.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="200.00", status="ACCEPTED")
        ApplicationModel.objects.create(
            competition_id=competition.id,
            applicant_id=uuid.uuid4(),
            status="PAID",
            total_price=ApplicationMapper._total_to_json(
                TotalPriceSnapshot(
                    total=Money.of("250.00", Currency.BYN),
                    submissions_total=Money.of("200.00", Currency.BYN),
                    services_total=Money.of("50.00", Currency.BYN),
                    calculated_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            ),
        )

        data = operator.get(_DASHBOARD).data["data"]

        # What the participant paid the organizer, reported as context...
        assert data["orderFees"] == "250.00"
        # ...and the 50.00 of services kept out of what the platform is owed.
        assert data["commissionBase"] == "200.00"
        assert data["accruedCommission"] == "20.00"

    def test_charges_the_per_performance_fee_from_the_headcounts(self, operator: APIClient) -> None:
        # The operator's own example: a solo at 2.50, a duet at 4.00 and an
        # eight-strong ensemble at 6.00 come to 12.50 — a figure no order total says
        # anything about.
        organization_id, competition = self._on_the_fee_schedule(operator)
        _performance(competition_id=competition.id, participants=1, price="300.00")
        _performance(competition_id=competition.id, participants=2, price="300.00")
        _performance(competition_id=competition.id, participants=8, price="300.00")
        # Cancelled, however many people were in it.
        _performance(competition_id=competition.id, participants=8, status="CANCELLED")

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        row = data["organizations"][0]
        assert row["billingModel"] == "PER_PERFORMANCE_FEE"
        assert row["accruedCommission"] == "12.50"
        assert data["accruedCommission"] == "12.50"
        # The entries' own prices are not a base under this model, and say so.
        assert row["commissionBase"] == "0.00"

    def test_breaks_the_fee_down_by_band_for_the_act(self, operator: APIClient) -> None:
        # The table the operator copies into an act: how many entries of each size,
        # at what price, for how much. Every band appears, including one nothing
        # fell into — a price list with rows missing cannot be checked against the
        # organizer's own copy.
        organization_id, competition = self._on_the_fee_schedule(operator)
        for _ in range(3):
            _performance(competition_id=competition.id, participants=1)
        _performance(competition_id=competition.id, participants=4)

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        breakdown = data["organizations"][0]["feeBreakdown"]
        assert [(row["rangeLabel"], row["performances"], row["unitAmount"], row["amount"]) for row in breakdown] == [
            ("1", 3, "2.50", "7.50"),
            ("2-5", 1, "4.00", "4.00"),
            ("6+", 0, "6.00", "0.00"),
        ]
        # The rows add up to the figure printed beside them.
        assert sum(Decimal(row["amount"]) for row in breakdown) == Decimal(data["organizations"][0]["accruedCommission"])

    def test_a_percentage_organization_gets_no_band_breakdown(self, operator: APIClient) -> None:
        organization_id, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="100.00")

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        assert data["organizations"][0]["feeBreakdown"] == []

    def test_records_what_the_organization_actually_paid(self, operator: APIClient) -> None:
        # The whole point of the receipts ledger: accrued and received are different
        # facts, and the console must not read one as the other.
        organization_id, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="1000.00")

        recorded = operator.post(
            _COMMISSION_PAYMENTS,
            {"organizationId": organization_id, "amount": "40.00", "receivedAt": "2026-03-20", "note": "п/п 114"},
            format="json",
        )
        assert recorded.status_code == 201, recorded.data

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        row = data["organizations"][0]
        assert row["accruedCommission"] == "100.00"
        assert row["receivedCommission"] == "40.00"
        assert row["commissionDebt"] == "60.00"
        assert data["commissionDebt"] == "60.00"

    def test_a_paid_up_organization_owes_nothing(self, operator: APIClient) -> None:
        organization_id, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="1000.00")
        operator.post(
            _COMMISSION_PAYMENTS,
            {"organizationId": organization_id, "amount": "100.00", "receivedAt": "2026-03-20"},
            format="json",
        )

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        row = data["organizations"][0]
        # Both figures asserted, not just their difference: a debt of zero is also
        # what two zeroes look like, and that is the reading this test must refuse.
        assert row["accruedCommission"] == "100.00"
        assert row["receivedCommission"] == "100.00"
        assert row["commissionDebt"] == "0.00"

    def test_a_struck_off_receipt_stops_counting(self, operator: APIClient) -> None:
        organization_id, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="1000.00")
        payment = operator.post(
            _COMMISSION_PAYMENTS,
            {"organizationId": organization_id, "amount": "100.00", "receivedAt": "2026-03-20"},
            format="json",
        ).data["data"]

        assert operator.delete(f"{_COMMISSION_PAYMENTS}/{payment['id']}").status_code == 204

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]
        assert data["organizations"][0]["receivedCommission"] == "0.00"
        assert data["organizations"][0]["commissionDebt"] == "100.00"

    def test_a_receipt_needs_an_organization_the_platform_knows(self, operator: APIClient) -> None:
        refused = operator.post(
            _COMMISSION_PAYMENTS,
            {"organizationId": str(uuid.uuid4()), "amount": "100.00", "receivedAt": "2026-03-20"},
            format="json",
        )

        assert refused.status_code == 400

    def test_narrows_the_money_to_a_period(self, operator: APIClient) -> None:
        # An act is written for a month, so the period is read off the day each
        # entry became chargeable — and off the day each receipt landed, so the two
        # sides of a month's act are the same month.
        organization_id, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="100.00", billed_on=date(2026, 2, 10))
        _performance(competition_id=competition.id, price="200.00", billed_on=date(2026, 3, 10))
        _performance(competition_id=competition.id, price="400.00", billed_on=date(2026, 4, 10))
        for received_at, amount in (("2026-02-20", "5.00"), ("2026-03-20", "11.00")):
            operator.post(
                _COMMISSION_PAYMENTS,
                {"organizationId": organization_id, "amount": amount, "receivedAt": received_at},
                format="json",
            )

        data = operator.get(f"{_DASHBOARD}?from=2026-03-01&to=2026-03-31").data["data"]

        assert data["periodApplies"] is True
        assert data["performances"] == 1
        assert data["commissionBase"] == "200.00"
        assert data["accruedCommission"] == "20.00"
        assert data["receivedCommission"] == "11.00"
        assert data["commissionDebt"] == "9.00"

    def test_without_a_period_every_entry_counts(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="100.00", billed_on=date(2026, 2, 10))
        _performance(competition_id=competition.id, price="200.00", billed_on=date(2026, 4, 10))
        # No history at all: unplaceable in a month, but real work all the same.
        _performance(competition_id=competition.id, price="300.00", billed_on=None)

        data = operator.get(_DASHBOARD).data["data"]

        assert data["periodApplies"] is False
        assert data["performances"] == 3
        assert data["commissionBase"] == "600.00"

    def test_an_undated_entry_drops_out_of_a_period(self, operator: APIClient) -> None:
        # Keeping it would put an undated charge into a month's act. Dropping it is
        # visible — the untimed total above still counts it — and a figure the
        # operator can see is missing beats one they cannot.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, price="300.00", billed_on=None)

        data = operator.get(f"{_DASHBOARD}?from=2026-01-01&to=2026-12-31").data["data"]

        assert data["performances"] == 0
        assert data["accruedCommission"] == "0.00"

    def test_the_funnel_ignores_the_period(self, operator: APIClient) -> None:
        # An order spans the weeks between being drafted and being paid, so it has
        # no one date to file it under. `periodApplies` is what lets the console say
        # which half of the screen the dates moved.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _order(competition_id=competition.id, status="SUBMITTED", amount="100.00")

        data = operator.get(f"{_DASHBOARD}?from=2026-03-01&to=2026-03-31").data["data"]

        assert data["applications"] == 1
        assert data["statusCounts"]["SUBMITTED"] == 1

    def test_filters_by_competition(self, operator: APIClient) -> None:
        _, wanted = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, other = self._connected_with_a_festival(operator, name="Созвездие", commission="10")
        _order(competition_id=wanted.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=other.id, status="SUBMITTED", amount="900.00")
        _performance(competition_id=wanted.id, price="100.00")
        _performance(competition_id=other.id, price="900.00")

        data = operator.get(f"{_DASHBOARD}?competitionId={wanted.id}").data["data"]

        assert data["applications"] == 1
        assert data["commissionBase"] == "100.00"
        # Expenses and receipts are per organization, never per festival.
        assert data["expensesApply"] is False

    def test_filters_by_organization(self, operator: APIClient) -> None:
        organization_id, wanted = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, other = self._connected_with_a_festival(operator, name="Созвездие", commission="10")
        _order(competition_id=wanted.id, status="PAID", amount="100.00")
        _order(competition_id=other.id, status="PAID", amount="900.00")

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        assert data["applications"] == 1
        assert [row["name"] for row in data["organizations"]] == ["Гармония"]

    def test_offers_the_competitions_to_filter_by(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")

        data = operator.get(_DASHBOARD).data["data"]

        assert str(competition.id) in [option["id"] for option in data["competitions"]]

    def test_counts_the_people_behind_the_entries(self, operator: APIClient) -> None:
        # A collective entry brings the people on its ``member_count``, not one.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _performance(competition_id=competition.id, participants=1)
        _performance(competition_id=competition.id, participants=8)

        data = operator.get(_DASHBOARD).data["data"]

        assert data["performances"] == 2
        assert data["participants"] == 9

    def test_an_entry_with_no_price_yet_counts_without_inventing_money(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        SubmissionModel.objects.create(
            competition_id=competition.id,
            applicant_id=uuid.uuid4(),
            status="ACCEPTED",
            participants=[{"id": str(uuid.uuid4()), "display_name": "Соло", "member_count": 1, "members": []}],
        )

        data = operator.get(_DASHBOARD).data["data"]

        assert data["performances"] == 1
        assert Decimal(data["commissionBase"]) == Decimal("0")


class TestAudience:
    """The head counts: cabinets, registry participants, teachers.

    Rows are created straight on the models the console counts, because that is what
    a projection is being tested against — the registries themselves are covered by
    their own contexts' suites.
    """

    def _participant(self, *, owner_id: uuid.UUID, archived: bool = False, deleted: bool = False) -> ParticipantRegistryModel:
        return ParticipantRegistryModel.objects.create(
            owner_id=owner_id,
            first_name="Мария",
            last_name="Ковалёва",
            birth_date="2015-04-01",
            gender="female",
            archived=archived,
            deleted_at=datetime(2026, 1, 1, tzinfo=UTC) if deleted else None,
        )

    def _teacher(self, *, owner_id: uuid.UUID, status: str = "ACTIVE", deleted: bool = False) -> TeacherModel:
        return TeacherModel.objects.create(
            owner_id=owner_id,
            first_name="Ольга",
            last_name="Петрова",
            role="Педагог по вокалу",
            status=status,
            deleted_at=datetime(2026, 1, 1, tzinfo=UTC) if deleted else None,
        )

    def test_counts_cabinets_participants_and_teachers(self, operator: APIClient) -> None:
        owner = uuid.UUID(_register(APIClient(), "parent@example.com"))
        self._participant(owner_id=owner)
        self._participant(owner_id=owner, archived=True)
        self._teacher(owner_id=owner)
        self._teacher(owner_id=owner, status="ARCHIVED")

        data = operator.get(_AUDIENCE).data["data"]

        # The operator's own account is a cabinet too — this is every registered one.
        assert data["cabinets"]["total"] == 2
        assert data["participants"] == {"total": 2, "archived": 1}
        assert data["teachers"] == {"total": 2, "archived": 1}

    def test_counts_a_confirmed_e_mail_separately(self, operator: APIClient) -> None:
        confirmed = uuid.UUID(_register(APIClient(), "confirmed@example.com"))
        UserModel.objects.filter(id=confirmed).update(email_verified_at=datetime(2026, 1, 1, tzinfo=UTC))

        data = operator.get(_AUDIENCE).data["data"]

        assert data["cabinets"]["total"] == 2
        assert data["cabinets"]["emailVerified"] == 1

    def test_an_erased_row_is_not_counted(self, operator: APIClient) -> None:
        # Soft-deleted means gone as far as the platform's own figures go: counting
        # erased accounts and participants would report an audience that left.
        owner = uuid.UUID(_register(APIClient(), "erased@example.com"))
        UserModel.objects.filter(id=owner).update(deleted_at=datetime(2026, 1, 1, tzinfo=UTC))
        self._participant(owner_id=owner, deleted=True)
        self._teacher(owner_id=owner, deleted=True)

        data = operator.get(_AUDIENCE).data["data"]

        assert data["cabinets"]["total"] == 1
        assert data["participants"]["total"] == 0
        assert data["teachers"]["total"] == 0

    def test_ignores_the_dashboard_filters(self, operator: APIClient) -> None:
        # A query string the endpoint does not take must not quietly narrow anything:
        # these counts are platform-wide by definition.
        self._participant(owner_id=uuid.uuid4())

        filtered = operator.get(f"{_AUDIENCE}?organizationId={uuid.uuid4()}").data["data"]

        assert filtered["participants"]["total"] == 1
