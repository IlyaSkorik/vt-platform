"""Оператор платформы заходит в кабинет организации.

Поддержка работает изнутри панели: «у вас не принимаются заявки» разбирают,
открыв кабинет организатора — с его фестивалями, его заявками и его настройками,
а не читая базу через плечо. Оператор называет организацию заголовком
``X-Acting-Organization``, и с этого момента запрос про неё.

Тесты идут через настоящий HTTP-край и проверяют обе стороны: что оператор
действительно оказывается внутри — и что заголовок не делает ровно ничего для
всех остальных.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.application.handlers import SetOrganizationModulesCommand
from apps.organization.composition import (
    build_provision_owner_handler,
    build_set_organization_modules_handler,
)
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import OrganizationId, StaffMembershipId, StaffUserId
from apps.organization.infrastructure.repositories import DjangoStaffMembershipRepository
from apps.organization.infrastructure.system import SystemClock
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_COMPETITIONS = "/api/v1/competitions"
_ORGANIZATIONS = "/api/v1/platform/organizations"
_ME = "/api/v1/users/me"
_HEADER = "HTTP_X_ACTING_ORGANIZATION"


class _Client(APIClient):
    """An ``APIClient`` that remembers its token.

    ``credentials()`` replaces the whole header set, so stepping into an
    organization and back out means re-sending the authorization header — and a
    test that re-sends it has to have kept it.
    """

    access: str = ""

    def acting_inside(self, organization_id: str) -> _Client:
        """From now on, working inside ``organization_id``."""
        self.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}", **{_HEADER: organization_id})
        return self

    def stepping_out(self) -> _Client:
        """From now on, nobody's panel."""
        self.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        return self


def _register(client: _Client, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Имя", "lastName": "Фамилия"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    client.access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {client.access}")
    return str(user_id)


def _make_owner_of(user_id: str, organization_id: str) -> None:
    membership, _ = StaffMembership.activate_for_owner(
        membership_id=StaffMembershipId.generate(),
        organization_id=OrganizationId.from_string(organization_id),
        user_id=StaffUserId.from_string(user_id),
        now=SystemClock().utcnow(),
    )
    DjangoStaffMembershipRepository().save(membership)


@pytest.fixture
def operator() -> _Client:
    client = _Client()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def first_organization(operator: _Client) -> _Client:
    """The platform's own organization, with its owner signed in."""
    client = _Client()
    user_id = _register(client, "first-owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


@pytest.fixture
def second_organization(operator: _Client) -> tuple[_Client, str]:
    """A newly connected organization, with its owner signed in."""
    organization = operator.post(
        _ORGANIZATIONS,
        {"name": "Созвездие", "ownerEmail": "second-owner@example.com", "commissionPercent": "10"},
        format="json",
    ).data["data"]
    client = _Client()
    user_id = _register(client, "second-owner@example.com")
    _make_owner_of(user_id, organization["id"])
    return client, organization["id"]


class TestTheOperatorStepsIn:
    def test_without_naming_an_organization_the_organizer_api_stays_shut(self, operator: _Client) -> None:
        # Оператор — сотрудник ни одной организации: его собственный вид на всё
        # это консоль, а не чужой кабинет. Так было и остаётся.
        assert operator.get(_COMPETITIONS).status_code == 403

    def test_naming_one_opens_its_panel(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        client, organization_id = second_organization
        client.post(_COMPETITIONS, {"title": "Созвездие — сезон", "season": "2025/2026"}, format="json")

        response = operator.acting_inside(organization_id).get(_COMPETITIONS)

        assert response.status_code == 200
        assert [row["title"] for row in response.data["data"]] == ["Созвездие — сезон"]

    def test_the_panel_is_that_organizations_and_no_one_elses(
        self, operator: _Client, first_organization: _Client, second_organization: tuple[_Client, str]
    ) -> None:
        client, organization_id = second_organization
        first_organization.post(_COMPETITIONS, {"title": "Взлёт — сезон", "season": "2025/2026"}, format="json")
        client.post(_COMPETITIONS, {"title": "Созвездие — сезон", "season": "2025/2026"}, format="json")

        titles = [row["title"] for row in operator.acting_inside(organization_id).get(_COMPETITIONS).data["data"]]

        assert titles == ["Созвездие — сезон"]

    def test_what_the_operator_sets_up_belongs_to_the_organization(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        """Полный доступ — это и есть смысл захода: не посмотреть, а настроить."""
        _, organization_id = second_organization

        created = operator.acting_inside(organization_id).post(_COMPETITIONS, {"title": "Собран поддержкой", "season": "2025/2026"}, format="json")

        assert created.status_code == 201
        assert str(CompetitionModel.objects.get(id=created.data["data"]["id"]).organizer_id) == organization_id

    def test_users_me_answers_as_that_organizations_staff(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        # Панель рисуется из этого ответа: скажи он правду об аккаунте, а не о
        # запросе, оператор увидел бы свой пустой кабинет, а каждый его вызов
        # уходил бы в чужой.
        _, organization_id = second_organization

        body = operator.acting_inside(organization_id).get(_ME).data["data"]

        assert body["staffMembership"] == {"role": "OWNER", "status": "ACTIVE", "organizationId": organization_id}
        assert body["platformAdmin"] is True
        assert "COMPETITIONS" in body["enabledModules"]

    def test_stepping_out_is_dropping_the_header(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        _, organization_id = second_organization
        assert operator.acting_inside(organization_id).get(_ME).data["data"]["staffMembership"] is not None

        operator.stepping_out()

        assert operator.get(_ME).data["data"]["staffMembership"] is None
        assert operator.get(_COMPETITIONS).status_code == 403


class TestTheHeaderMeansNothingToAnybodyElse:
    def test_an_organizer_cannot_point_it_at_a_neighbour(self, first_organization: _Client, second_organization: tuple[_Client, str]) -> None:
        """Заголовок, который может выставить кто угодно, выставил бы прежде всего чужой."""
        client, organization_id = second_organization
        client.post(_COMPETITIONS, {"title": "Созвездие — сезон", "season": "2025/2026"}, format="json")
        first_organization.post(_COMPETITIONS, {"title": "Взлёт — сезон", "season": "2025/2026"}, format="json")

        titles = [row["title"] for row in first_organization.acting_inside(organization_id).get(_COMPETITIONS).data["data"]]

        assert titles == ["Взлёт — сезон"]

    def test_an_organization_that_is_not_there_is_not_stepped_into(self, operator: _Client) -> None:
        assert operator.acting_inside(str(uuid.uuid4())).get(_COMPETITIONS).status_code == 403

    def test_a_malformed_id_is_read_as_no_organization_at_all(self, operator: _Client) -> None:
        assert operator.acting_inside("не-uuid").get(_COMPETITIONS).status_code == 403


class TestInsideThePanelTheModulesAreTheOrganizationsOwn:
    def test_a_module_the_organization_never_bought_stays_shut(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        """Внутри кабинета оператор видит то же, что организатор.

        Включить модуль он может — но в консоли, где это решение видно и
        датировано, а не молча изнутри чужой панели.
        """
        _, organization_id = second_organization
        build_set_organization_modules_handler().handle(SetOrganizationModulesCommand(organization_id=organization_id, modules=("VOTING",)))

        response = operator.acting_inside(organization_id).get(_COMPETITIONS)

        assert response.status_code == 403
        assert "не подключён" in str(response.data["detail"])

    def test_and_the_modules_it_did_are_open(self, operator: _Client, second_organization: tuple[_Client, str]) -> None:
        _, organization_id = second_organization
        build_set_organization_modules_handler().handle(
            SetOrganizationModulesCommand(organization_id=organization_id, modules=("VOTING", "COMPETITIONS"))
        )

        assert operator.acting_inside(organization_id).get(_COMPETITIONS).status_code == 200
