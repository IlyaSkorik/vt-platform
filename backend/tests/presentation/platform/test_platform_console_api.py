"""Integration tests for the platform operator's console.

The console is what sits above every organization: connecting new ones, setting
what each owes the platform, and reading the pipeline across all of them. Access
comes only from the ``grant_platform_admin`` command, so these tests grant it the
same way the deployment would.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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


def _submission_ref(*, competition_id: uuid.UUID, participants: int) -> dict[str, object]:
    """One performance of ``participants`` people, and the order-level reference to it.

    The headcount lives on the submission (as one collective entry carrying a
    ``member_count``, the way the Submission mapper writes it) because that is where
    the per-performance fee reads it from; the order only points at the submission.
    """
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"id": str(uuid.uuid4()), "display_name": "Ансамбль", "member_count": participants, "members": []}],
    )
    return {
        "submission_id": str(submission.id),
        "performance_title": f"Номер на {participants}",
        "participant_display_name": "Ансамбль",
        "nomination": "Вокал",
        "discipline": "Эстрадный вокал",
        "status": "SUBMITTED",
        "price": None,
    }


def _order(
    *,
    competition_id: uuid.UUID,
    status: str,
    amount: str | None,
    performances: tuple[int, ...] = (),
) -> ApplicationModel:
    return ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        total_price=_total_price(amount) if amount is not None else None,
        submission_refs=[_submission_ref(competition_id=competition_id, participants=count) for count in performances],
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

    def test_projects_the_commission_from_the_fees(self, operator: APIClient) -> None:
        # A cancelled order is not revenue and must not inflate the projection;
        # a paid one counts towards both the expected and the settled figure.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _order(competition_id=competition.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=competition.id, status="PAID", amount="200.00")
        _order(competition_id=competition.id, status="CANCELLED", amount="500.00")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["expectedFees"] == "300.00"
        assert data["settledFees"] == "200.00"
        assert data["expectedCommission"] == "30.00"
        assert data["settledCommission"] == "20.00"

    def test_projects_the_per_performance_fee_from_the_headcounts(self, operator: APIClient) -> None:
        # The operator's own example: a solo at 2.50, a duet at 4.00 and an
        # eight-strong ensemble at 6.00 come to 12.50 for the order — a figure the
        # order's own total (900.00 of participation fees) says nothing about.
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
        _order(competition_id=competition.id, status="PAID", amount="900.00", performances=(1, 2, 8))
        # A cancelled order is billable to nobody, however many performances it held.
        _order(competition_id=competition.id, status="CANCELLED", amount="900.00", performances=(1, 2, 8))

        data = operator.get(f"{_DASHBOARD}?organizationId={organization['id']}").data["data"]

        row = data["organizations"][0]
        assert row["billingModel"] == "PER_PERFORMANCE_FEE"
        assert row["expectedCommission"] == "12.50"
        assert row["settledCommission"] == "12.50"
        assert data["expectedCommission"] == "12.50"
        # The fees themselves are still reported; they are simply not what is owed.
        assert row["expectedFees"] == "900.00"

    def test_filters_by_competition(self, operator: APIClient) -> None:
        _, wanted = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, other = self._connected_with_a_festival(operator, name="Созвездие", commission="10")
        _order(competition_id=wanted.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=other.id, status="SUBMITTED", amount="900.00")

        data = operator.get(f"{_DASHBOARD}?competitionId={wanted.id}").data["data"]

        assert data["applications"] == 1
        assert data["expectedFees"] == "100.00"

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

    def test_reads_the_price_shape_the_mapper_actually_writes(self, operator: APIClient) -> None:
        # The console once read the total under a key nothing ever wrote, so every
        # order showed as free while the counts looked right. Priced here through
        # the mapper itself, so the console and the writer cannot drift apart again.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        snapshot = TotalPriceSnapshot(
            total=Money.of("250.00", Currency.BYN),
            submissions_total=Money.of("200.00", Currency.BYN),
            services_total=Money.of("50.00", Currency.BYN),
            calculated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        ApplicationModel.objects.create(
            competition_id=competition.id,
            applicant_id=uuid.uuid4(),
            status="PAID",
            # Deliberately the mapper's own writer: it is the contract under test.
            total_price=ApplicationMapper._total_to_json(snapshot),
        )

        data = operator.get(_DASHBOARD).data["data"]

        assert data["settledFees"] == "250.00"
        assert data["settledCommission"] == "25.00"

    def test_an_order_with_no_price_yet_counts_without_inventing_money(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _order(competition_id=competition.id, status="SUBMITTED", amount=None)

        data = operator.get(_DASHBOARD).data["data"]

        assert data["applications"] == 1
        assert Decimal(data["expectedFees"]) == Decimal("0")


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
