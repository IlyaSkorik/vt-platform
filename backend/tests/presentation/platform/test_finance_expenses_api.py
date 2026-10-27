"""Integration tests for the platform's expense book and the profit it produces.

Two things are under test and they are different kinds of thing. One is the ledger
itself — the operator entering what the platform spent, correcting a figure,
striking one out. The other is the arithmetic on the console's summary: commission
actually received, recorded costs out, and the difference that says whether the
platform is ahead or behind. Commission is accrued per entry and received by hand,
so these fixtures write entries and receipts rather than orders.

Access is granted the way the deployment grants it, through
``grant_platform_admin``: an organization's own OWNER must not be able to read what
the platform spends, least of all the part of it recorded against them.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.finance.infrastructure.models import PlatformExpenseModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_EXPENSES = "/api/v1/platform/expenses"
_ORGANIZATIONS = "/api/v1/platform/organizations"
_DASHBOARD = "/api/v1/platform/dashboard"
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


def _expense(
    operator: APIClient,
    *,
    amount: str,
    purpose: str,
    category: str = "OTHER",
    spent_at: str = "2026-03-01",
    organization_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"amount": amount, "category": category, "purpose": purpose, "spentAt": spent_at}
    if organization_id is not None:
        payload["organizationId"] = organization_id
    response = operator.post(_EXPENSES, payload, format="json")
    assert response.status_code == 201, response.data
    return dict(response.data["data"])


def _connected(operator: APIClient, *, name: str, commission: str) -> str:
    organization = operator.post(
        _ORGANIZATIONS,
        {"name": name, "ownerEmail": f"{uuid.uuid4().hex[:8]}@example.com", "commissionPercent": commission},
        format="json",
    ).data["data"]
    return str(organization["id"])


def _performance(*, competition_id: uuid.UUID, price: str, billed_on: str = "2026-03-15") -> None:
    """One billable entry — the unit commission is actually counted from.

    Written the way the Submission mapper writes one, including the transition into
    ``PAID`` the period filter reads, so these fixtures cannot drift from what the
    console reads.
    """
    SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        participants=[{"id": str(uuid.uuid4()), "display_name": "Соло", "member_count": 1, "members": []}],
        price_snapshot={"amount": price, "currency": "BYN", "calculated_at": "2026-01-01T00:00:00+00:00"},
        status_history=[{"from_status": "WAITING_PAYMENT", "to_status": "PAID", "occurred_at": f"{billed_on}T12:00:00+00:00"}],
    )


def _received(operator: APIClient, *, organization_id: str, amount: str, received_at: str = "2026-03-20") -> None:
    """Commission the operator records as actually paid."""
    response = operator.post(
        _COMMISSION_PAYMENTS,
        {"organizationId": organization_id, "amount": amount, "receivedAt": received_at},
        format="json",
    )
    assert response.status_code == 201, response.data


class TestAccess:
    def test_an_anonymous_caller_is_refused(self) -> None:
        assert APIClient().get(_EXPENSES).status_code == 401

    def test_an_organization_owner_cannot_read_what_the_platform_spends(self, organization_owner: APIClient) -> None:
        # The expense book has one audience. An organization's own OWNER is the top
        # of that organization and still on the other side of this line — not least
        # because some of these rows are recorded against them.
        assert organization_owner.get(_EXPENSES).status_code == 403
        assert organization_owner.post(_EXPENSES, {}, format="json").status_code == 403

    def test_the_operator_is_admitted(self, operator: APIClient) -> None:
        assert operator.get(_EXPENSES).status_code == 200


class TestRecordingAnExpense:
    def test_records_a_cost_with_what_it_was_for(self, operator: APIClient) -> None:
        data = _expense(operator, amount="120.50", purpose="Хостинг за март", category="INFRASTRUCTURE")

        assert data["amount"] == "120.50"
        assert data["purpose"] == "Хостинг за март"
        assert data["category"] == "INFRASTRUCTURE"
        assert data["organizationId"] is None
        assert PlatformExpenseModel.objects.filter(deleted_at__isnull=True).count() == 1

    def test_accepts_the_ordinary_russian_spelling_of_a_sum(self, operator: APIClient) -> None:
        # "1 200,50" is what a Russian invoice says and what a Russian keyboard
        # types. Refusing it would be refusing the normal spelling of the number.
        data = _expense(operator, amount="1 200,50", purpose="Реклама")

        assert data["amount"] == "1200.50"

    def test_refuses_a_cost_with_no_purpose(self, operator: APIClient) -> None:
        response = operator.post(
            _EXPENSES,
            {"amount": "10.00", "category": "OTHER", "purpose": "   ", "spentAt": "2026-03-01"},
            format="json",
        )

        assert response.status_code == 400

    def test_refuses_a_sum_that_is_not_a_cost(self, operator: APIClient) -> None:
        for amount in ("0", "-40.00", "не число"):
            response = operator.post(
                _EXPENSES,
                {"amount": amount, "category": "OTHER", "purpose": "Что-то", "spentAt": "2026-03-01"},
                format="json",
            )
            assert response.status_code == 400, amount

    def test_refuses_an_article_that_is_not_on_the_list(self, operator: APIClient) -> None:
        response = operator.post(
            _EXPENSES,
            {"amount": "10.00", "category": "ВЫДУМАННАЯ", "purpose": "Что-то", "spentAt": "2026-03-01"},
            format="json",
        )

        assert response.status_code == 400

    def test_names_the_organization_a_cost_was_carried_for(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")

        data = _expense(operator, amount="50.00", purpose="Печать дипломов", organization_id=organization)

        assert data["organizationId"] == organization
        assert data["organizationName"] == "Гармония"


class TestTheLedger:
    def test_totals_the_rows_in_scope_and_groups_them_by_article(self, operator: APIClient) -> None:
        _expense(operator, amount="100.00", purpose="Хостинг", category="INFRASTRUCTURE")
        _expense(operator, amount="40.00", purpose="Домен", category="INFRASTRUCTURE")
        _expense(operator, amount="500.00", purpose="Таргет", category="MARKETING")

        data = operator.get(_EXPENSES).data["data"]

        assert data["total"] == "640.00"
        # Largest article first: the operator reads this to find where the money went.
        assert [row["category"] for row in data["byCategory"]] == ["MARKETING", "INFRASTRUCTURE"]
        assert data["byCategory"][1]["amount"] == "140.00"
        assert data["byCategory"][1]["count"] == 2

    def test_narrows_to_one_organization(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        _expense(operator, amount="60.00", purpose="Печать", organization_id=organization)
        _expense(operator, amount="900.00", purpose="Сервер", category="INFRASTRUCTURE")

        data = operator.get(f"{_EXPENSES}?organizationId={organization}").data["data"]

        assert data["total"] == "60.00"
        assert len(data["expenses"]) == 1

    def test_narrows_to_a_period_by_the_day_the_money_went(self, operator: APIClient) -> None:
        _expense(operator, amount="10.00", purpose="Февраль", spent_at="2026-02-20")
        _expense(operator, amount="20.00", purpose="Март", spent_at="2026-03-15")
        _expense(operator, amount="40.00", purpose="Апрель", spent_at="2026-04-02")

        data = operator.get(f"{_EXPENSES}?from=2026-03-01&to=2026-03-31").data["data"]

        assert data["total"] == "20.00"
        assert [row["purpose"] for row in data["expenses"]] == ["Март"]

    def test_a_half_typed_date_narrows_nothing_rather_than_failing(self, operator: APIClient) -> None:
        _expense(operator, amount="10.00", purpose="Хостинг")

        response = operator.get(f"{_EXPENSES}?from=2026-0")

        assert response.status_code == 200
        assert response.data["data"]["total"] == "10.00"


class TestCorrectingAndRemoving:
    def test_corrects_a_mistyped_figure(self, operator: APIClient) -> None:
        recorded = _expense(operator, amount="1000.00", purpose="Хостинг")

        response = operator.patch(f"{_EXPENSES}/{recorded['id']}", {"amount": "100.00"}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["data"]["amount"] == "100.00"
        # Everything the caller left out is left alone.
        assert response.data["data"]["purpose"] == "Хостинг"

    def test_moves_a_cost_off_a_client_and_onto_the_platform(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        recorded = _expense(operator, amount="80.00", purpose="Печать", organization_id=organization)

        # An explicit null is the payload that means it; omitting the key entirely
        # would leave the attribution alone, which is the next assertion.
        moved = operator.patch(f"{_EXPENSES}/{recorded['id']}", {"organizationId": None}, format="json")

        assert moved.status_code == 200, moved.data
        assert moved.data["data"]["organizationId"] is None

    def test_an_omitted_organization_leaves_the_attribution_alone(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        recorded = _expense(operator, amount="80.00", purpose="Печать", organization_id=organization)

        amended = operator.patch(f"{_EXPENSES}/{recorded['id']}", {"purpose": "Печать дипломов"}, format="json")

        assert amended.data["data"]["organizationId"] == organization

    def test_strikes_a_cost_out_without_erasing_the_row(self, operator: APIClient) -> None:
        recorded = _expense(operator, amount="80.00", purpose="Ошибка")

        assert operator.delete(f"{_EXPENSES}/{recorded['id']}").status_code == 204

        assert operator.get(_EXPENSES).data["data"]["total"] == "0.00"
        # The row stays: last month's total has to remain explainable.
        assert PlatformExpenseModel.objects.filter(pk=str(recorded["id"])).exists()

    def test_a_cost_that_is_not_there_is_a_404(self, operator: APIClient) -> None:
        assert operator.delete(f"{_EXPENSES}/{uuid.uuid4()}").status_code == 404
        assert operator.patch(f"{_EXPENSES}/не-идентификатор", {"amount": "1.00"}, format="json").status_code == 404


class TestProfitOnTheDashboard:
    def _festival_of(self, organization_id: str, *, title: str) -> CompetitionModel:
        return CompetitionModel.objects.create(
            organizer_id=uuid.UUID(organization_id),
            status="PUBLISHED",
            title=title,
            season="2025/2026",
        )

    def test_subtracts_the_recorded_costs_from_what_was_actually_paid(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        festival = self._festival_of(organization, title="Гармония — сезон")
        # 300.00 of entries at 10% is 30.00 accrued; 20.00 of it has arrived.
        _performance(competition_id=festival.id, price="200.00")
        _performance(competition_id=festival.id, price="100.00")
        _received(operator, organization_id=organization, amount="20.00")
        _expense(operator, amount="25.00", purpose="Печать дипломов", organization_id=organization)

        data = operator.get(_DASHBOARD).data["data"]

        assert data["accruedCommission"] == "30.00"
        assert data["receivedCommission"] == "20.00"
        assert data["commissionDebt"] == "10.00"
        assert data["expenses"] == "25.00"
        # Profit is money in hand less money out, and nothing else: 20.00 received
        # against 25.00 spent. The 10.00 still owed is reported as a debt rather
        # than folded into a profit figure it has not become yet.
        assert data["profit"] == "-5.00"
        assert data["expensesApply"] is True

    def test_gives_each_organization_its_own_line(self, operator: APIClient) -> None:
        first = _connected(operator, name="Гармония", commission="10")
        second = _connected(operator, name="Созвездие", commission="10")
        _performance(competition_id=self._festival_of(first, title="Г").id, price="1000.00")
        _performance(competition_id=self._festival_of(second, title="С").id, price="1000.00")
        _received(operator, organization_id=first, amount="100.00")
        _received(operator, organization_id=second, amount="100.00")
        _expense(operator, amount="30.00", purpose="Печать", organization_id=first)
        _expense(operator, amount="400.00", purpose="Сервер", category="INFRASTRUCTURE")

        rows = {row["name"]: row for row in operator.get(_DASHBOARD).data["data"]["organizations"]}

        assert rows["Гармония"]["expenses"] == "30.00"
        assert rows["Гармония"]["profit"] == "70.00"
        assert rows["Созвездие"]["expenses"] == "0.00"
        assert rows["Созвездие"]["profit"] == "100.00"

    def test_the_platform_total_includes_the_overheads_no_line_carries(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        _performance(competition_id=self._festival_of(organization, title="Г").id, price="1000.00")
        _received(operator, organization_id=organization, amount="100.00")
        _expense(operator, amount="30.00", purpose="Печать", organization_id=organization)
        _expense(operator, amount="400.00", purpose="Сервер", category="INFRASTRUCTURE")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["expenses"] == "430.00"
        assert data["unattributedExpenses"] == "400.00"
        # 100.00 of commission against 430.00 of costs — the number the operator
        # opened this screen for.
        assert data["profit"] == "-330.00"

    def test_narrowing_to_one_organization_drops_the_platform_overheads(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        _performance(competition_id=self._festival_of(organization, title="Г").id, price="1000.00")
        _received(operator, organization_id=organization, amount="100.00")
        _expense(operator, amount="30.00", purpose="Печать", organization_id=organization)
        _expense(operator, amount="400.00", purpose="Сервер", category="INFRASTRUCTURE")

        data = operator.get(f"{_DASHBOARD}?organizationId={organization}").data["data"]

        # A server bill is not part of whether this client is profitable.
        assert data["expenses"] == "30.00"
        assert data["profit"] == "70.00"

    def test_a_competition_filter_says_the_expenses_do_not_apply(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония", commission="10")
        festival = self._festival_of(organization, title="Г")
        _performance(competition_id=festival.id, price="1000.00")
        _expense(operator, amount="30.00", purpose="Печать", organization_id=organization)

        data = operator.get(f"{_DASHBOARD}?competitionId={festival.id}").data["data"]

        # Costs are recorded per organization and never per festival, so there is
        # nothing honest to subtract here — and the console is told so rather than
        # shown an organization-wide figure against one festival's commission.
        assert data["expensesApply"] is False
        assert data["expenses"] == "0.00"
