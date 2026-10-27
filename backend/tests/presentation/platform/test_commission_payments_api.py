"""Integration tests for the commission the platform has actually been paid.

The ledger that answers "кто ещё должен?". What an organization owes is derived
from its entries and nobody types it in; whether the money arrived is a fact only
a bank statement carries, and this is where the operator enters it.

Access is granted the way the deployment grants it, through
``grant_platform_admin``: what organizations pay the platform is not an
organization's business, least of all the rows naming another client.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.finance.infrastructure.models import CommissionPaymentModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_PAYMENTS = "/api/v1/platform/commission-payments"
_ORGANIZATIONS = "/api/v1/platform/organizations"


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


def _connected(operator: APIClient, *, name: str) -> str:
    organization = operator.post(
        _ORGANIZATIONS,
        {"name": name, "ownerEmail": f"{uuid.uuid4().hex[:8]}@example.com", "commissionPercent": "10"},
        format="json",
    ).data["data"]
    return str(organization["id"])


def _received(
    operator: APIClient,
    *,
    organization_id: str,
    amount: str,
    received_at: str = "2026-03-20",
    note: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"organizationId": organization_id, "amount": amount, "receivedAt": received_at}
    if note is not None:
        payload["note"] = note
    response = operator.post(_PAYMENTS, payload, format="json")
    assert response.status_code == 201, response.data
    return dict(response.data["data"])


class TestAccess:
    def test_an_anonymous_caller_is_refused(self) -> None:
        assert APIClient().get(_PAYMENTS).status_code == 401

    def test_an_organization_owner_cannot_read_what_other_clients_paid(self, organization_owner: APIClient) -> None:
        assert organization_owner.get(_PAYMENTS).status_code == 403
        assert organization_owner.post(_PAYMENTS, {}, format="json").status_code == 403

    def test_the_operator_is_admitted(self, operator: APIClient) -> None:
        assert operator.get(_PAYMENTS).status_code == 200


class TestRecordingAPayment:
    def test_records_who_paid_how_much_and_when(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")

        data = _received(operator, organization_id=organization, amount="250.00", note="п/п 114")

        assert data["organizationId"] == organization
        assert data["organizationName"] == "Гармония"
        assert data["amount"] == "250.00"
        assert str(data["receivedAt"]) == "2026-03-20"
        assert data["note"] == "п/п 114"
        assert CommissionPaymentModel.objects.filter(deleted_at__isnull=True).count() == 1

    def test_accepts_the_ordinary_russian_spelling_of_a_sum(self, operator: APIClient) -> None:
        # The figure is copied off a payment order, where it is written like this.
        organization = _connected(operator, name="Гармония")

        data = _received(operator, organization_id=organization, amount="1 200,50")

        assert data["amount"] == "1200.50"

    def test_a_payment_needs_a_payer(self, operator: APIClient) -> None:
        # The difference from an expense: the platform can carry a cost itself, but
        # money that reduces nobody's debt is not a payment.
        response = operator.post(_PAYMENTS, {"amount": "10.00", "receivedAt": "2026-03-20"}, format="json")

        assert response.status_code == 400

    def test_refuses_an_organization_the_platform_has_never_connected(self, operator: APIClient) -> None:
        # A stale or typed-in id would park money against a client that appears in
        # no total — the money would be in the books and in nobody's line.
        response = operator.post(
            _PAYMENTS,
            {"organizationId": str(uuid.uuid4()), "amount": "10.00", "receivedAt": "2026-03-20"},
            format="json",
        )

        assert response.status_code == 400

    def test_refuses_a_sum_that_is_not_a_payment(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        for amount in ("0", "-40.00", "не число"):
            response = operator.post(
                _PAYMENTS,
                {"organizationId": organization, "amount": amount, "receivedAt": "2026-03-20"},
                format="json",
            )
            assert response.status_code == 400, amount


class TestTheLedger:
    def test_totals_the_rows_in_scope_and_groups_them_by_payer(self, operator: APIClient) -> None:
        first = _connected(operator, name="Гармония")
        second = _connected(operator, name="Созвездие")
        _received(operator, organization_id=first, amount="100.00")
        _received(operator, organization_id=first, amount="40.00")
        _received(operator, organization_id=second, amount="500.00")

        data = operator.get(_PAYMENTS).data["data"]

        assert data["total"] == "640.00"
        # Largest payer first: the operator reads this to see where the money came from.
        assert [(row["organizationName"], row["amount"], row["count"]) for row in data["byOrganization"]] == [
            ("Созвездие", "500.00", 1),
            ("Гармония", "140.00", 2),
        ]

    def test_narrows_to_one_payer(self, operator: APIClient) -> None:
        first = _connected(operator, name="Гармония")
        second = _connected(operator, name="Созвездие")
        _received(operator, organization_id=first, amount="100.00")
        _received(operator, organization_id=second, amount="500.00")

        data = operator.get(f"{_PAYMENTS}?organizationId={first}").data["data"]

        assert data["total"] == "100.00"
        assert len(data["payments"]) == 1

    def test_narrows_to_a_period_by_the_day_the_money_landed(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        _received(operator, organization_id=organization, amount="100.00", received_at="2026-02-20")
        _received(operator, organization_id=organization, amount="40.00", received_at="2026-03-20")
        _received(operator, organization_id=organization, amount="7.00", received_at="2026-04-20")

        data = operator.get(f"{_PAYMENTS}?from=2026-03-01&to=2026-03-31").data["data"]

        assert data["total"] == "40.00"

    def test_a_half_typed_date_narrows_nothing_rather_than_erroring(self, operator: APIClient) -> None:
        # These are the two ends of a filter on a screen; a date mid-keystroke in
        # the address bar must not blank the ledger.
        organization = _connected(operator, name="Гармония")
        _received(operator, organization_id=organization, amount="100.00")

        response = operator.get(f"{_PAYMENTS}?from=2026-0")

        assert response.status_code == 200
        assert response.data["data"]["total"] == "100.00"

    def test_newest_first(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        _received(operator, organization_id=organization, amount="1.00", received_at="2026-01-10")
        _received(operator, organization_id=organization, amount="2.00", received_at="2026-05-10")

        rows = operator.get(_PAYMENTS).data["data"]["payments"]

        assert [row["amount"] for row in rows] == ["2.00", "1.00"]


class TestCorrectingAPayment:
    def test_fixes_a_mistyped_sum(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        recorded = _received(operator, organization_id=organization, amount="2500.00")

        amended = operator.patch(f"{_PAYMENTS}/{recorded['id']}", {"amount": "250.00"}, format="json")

        assert amended.status_code == 200, amended.data
        assert amended.data["data"]["amount"] == "250.00"

    def test_re_points_a_payment_credited_to_the_wrong_client(self, operator: APIClient) -> None:
        first = _connected(operator, name="Гармония")
        second = _connected(operator, name="Созвездие")
        recorded = _received(operator, organization_id=first, amount="250.00")

        amended = operator.patch(f"{_PAYMENTS}/{recorded['id']}", {"organizationId": second}, format="json")

        assert amended.data["data"]["organizationId"] == second
        assert amended.data["data"]["organizationName"] == "Созвездие"

    def test_an_omitted_payer_leaves_it_alone(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        recorded = _received(operator, organization_id=organization, amount="250.00")

        amended = operator.patch(f"{_PAYMENTS}/{recorded['id']}", {"note": "п/п 115"}, format="json")

        assert amended.data["data"]["organizationId"] == organization

    def test_refuses_to_re_point_at_an_organization_that_is_not_connected(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        recorded = _received(operator, organization_id=organization, amount="250.00")

        amended = operator.patch(
            f"{_PAYMENTS}/{recorded['id']}",
            {"organizationId": str(uuid.uuid4())},
            format="json",
        )

        assert amended.status_code == 400

    def test_strikes_a_payment_out_without_erasing_the_row(self, operator: APIClient) -> None:
        organization = _connected(operator, name="Гармония")
        recorded = _received(operator, organization_id=organization, amount="250.00")

        assert operator.delete(f"{_PAYMENTS}/{recorded['id']}").status_code == 204

        assert operator.get(_PAYMENTS).data["data"]["total"] == "0.00"
        # The row stays: last month's debt total has to remain explainable.
        assert CommissionPaymentModel.objects.filter(pk=str(recorded["id"])).exists()

    def test_a_payment_that_is_not_there_is_a_404(self, operator: APIClient) -> None:
        assert operator.delete(f"{_PAYMENTS}/{uuid.uuid4()}").status_code == 404
        assert operator.patch(f"{_PAYMENTS}/не-идентификатор", {"amount": "1.00"}, format="json").status_code == 404
