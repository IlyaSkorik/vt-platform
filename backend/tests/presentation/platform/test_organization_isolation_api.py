"""The boundary between two connected organizations.

Connecting a second organization is only safe if its people cannot see the first
one's work. These tests drive both sides through the real HTTP edge: two
organizations, two owners, one festival each, and every crossing refused.
"""

from __future__ import annotations

import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import ApplicationModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    GenerationRunModel,
    PrintJobModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import OrganizationId, StaffMembershipId, StaffUserId
from apps.organization.infrastructure.repositories import DjangoStaffMembershipRepository
from apps.organization.infrastructure.system import SystemClock
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_COMPETITIONS = "/api/v1/competitions"
_WORKSPACE = "/api/v1/staff/applications/workspace"
_ARCHIVE = "/api/v1/staff/applications/documents.zip"
_ORGANIZATIONS = "/api/v1/platform/organizations"
_TEMPLATES = "/api/v1/staff/diplomas/templates"
_ASSIGNMENTS = "/api/v1/staff/diplomas/assignments"
_REGISTRY = "/api/v1/staff/diplomas/registry"
_GENERATION_ARCHIVE = "/api/v1/staff/diplomas/generation-archive"


def _register(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Имя", "lastName": "Фамилия"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return str(user_id)


def _make_owner_of(user_id: str, organization_id: str) -> None:
    """Activate an OWNER membership directly — the invitation flow's end state."""
    membership, _ = StaffMembership.activate_for_owner(
        membership_id=StaffMembershipId.generate(),
        organization_id=OrganizationId.from_string(organization_id),
        user_id=StaffUserId.from_string(user_id),
        now=SystemClock().utcnow(),
    )
    DjangoStaffMembershipRepository().save(membership)


@pytest.fixture
def operator() -> APIClient:
    client = APIClient()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def first_organization(operator: APIClient) -> APIClient:
    """The platform's own organization, with its owner signed in."""
    client = APIClient()
    user_id = _register(client, "first-owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


@pytest.fixture
def second_organization(operator: APIClient) -> tuple[APIClient, str]:
    """A newly connected organization, with its owner signed in."""
    organization = operator.post(
        _ORGANIZATIONS,
        {"name": "Созвездие", "ownerEmail": "second-owner@example.com", "commissionPercent": "10"},
        format="json",
    ).data["data"]
    client = APIClient()
    user_id = _register(client, "second-owner@example.com")
    _make_owner_of(user_id, organization["id"])
    return client, organization["id"]


def _create_competition(client: APIClient, title: str) -> str:
    response = client.post(_COMPETITIONS, {"title": title, "season": "2025/2026"}, format="json")
    assert response.status_code == 201, response.data
    return str(response.data["data"]["id"])


class TestCompetitionsAreScopedToTheirOrganization:
    def test_a_competition_is_filed_under_the_creators_organization(self, second_organization: tuple[APIClient, str]) -> None:
        client, organization_id = second_organization
        competition_id = _create_competition(client, "Созвездие — сезон")

        stored = CompetitionModel.objects.get(id=competition_id)
        assert str(stored.organizer_id) == organization_id

    def test_the_list_shows_only_the_callers_own(self, first_organization: APIClient, second_organization: tuple[APIClient, str]) -> None:
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        first_titles = [row["title"] for row in first_organization.get(_COMPETITIONS).data["data"]]
        second_titles = [row["title"] for row in client.get(_COMPETITIONS).data["data"]]

        assert "Взлёт — сезон" in first_titles
        assert "Созвездие — сезон" not in first_titles
        assert second_titles == ["Созвездие — сезон"]

    def test_reaching_another_organizations_competition_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        assert client.get(f"{_COMPETITIONS}/{theirs}").status_code == 403
        assert client.post(f"{_COMPETITIONS}/{theirs}/categories", {"name": "Вокал"}, format="json").status_code == 403

    def test_the_platform_operator_reads_across_organizations_from_their_own_console(
        self, operator: APIClient, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        # Not through the organizer API: that one belongs to an organization's
        # staff, and the operator is staff of none. Their view of everything is
        # the platform console, which is read-only about other people's festivals.
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        assert operator.get(_COMPETITIONS).status_code == 403

        titles = [option["title"] for option in operator.get("/api/v1/platform/dashboard").data["data"]["competitions"]]
        assert {"Взлёт — сезон", "Созвездие — сезон"} <= set(titles)


class TestApplicationsAreScopedToTheirOrganization:
    def _order_for(self, competition_id: str) -> None:
        ApplicationModel.objects.create(
            competition_id=uuid.UUID(competition_id),
            applicant_id=uuid.uuid4(),
            status="SUBMITTED",
            total_price={
                "total": "100.00",
                "submissions_total": "100.00",
                "services_total": "0.00",
                "currency": "BYN",
                "calculated_at": "2026-01-01T00:00:00+00:00",
            },
        )

    def test_the_workspace_offers_only_the_callers_competitions(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        data = client.get(_WORKSPACE).data["data"]
        titles = [row["title"] for row in data["filters"]["competitions"]] if "filters" in data else []

        assert "Взлёт — сезон" not in titles

    def test_the_paperwork_archive_stops_at_the_organization_boundary(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")
        self._order_for(theirs)

        response = client.get(f"{_ARCHIVE}?competitionId={theirs}")

        assert response.status_code == 200
        # Nothing of the other organization's — the filter cannot widen the scope.
        # A ZIP download is a streamed FileResponse; the test client's response type is
        # the non-streaming alias, so the body is reached through the concrete class.
        assert isinstance(response, StreamingHttpResponse)
        assert b"".join(response.streaming_content)


def _create_template(client: APIClient, name: str, document_type: str = "DIPLOMA") -> str:
    response = client.post(_TEMPLATES, {"name": name, "type": document_type}, format="json")
    assert response.status_code == 201, response.data
    return str(response.data["data"]["id"])


def _create_nomination(client: APIClient, competition_id: str, name: str = "Вокал") -> str:
    response = client.post(f"{_COMPETITIONS}/{competition_id}/categories", {"name": name}, format="json")
    assert response.status_code in {200, 201}, response.data
    payload = response.data["data"]
    # The endpoint answers with the refreshed competition, so the new nomination is
    # the one that was not there before — and with one competition per test, the last.
    return str(payload["categories"][-1]["id"])


class TestDiplomaTemplatesAreScopedToTheirOrganization:
    """A diploma design is the one thing an organizer would least like shared.

    Before templates carried an owner the whole library was global: every organizer
    listed every organization's designs, and could open, re-upload and overwrite any
    of them by id. These tests drive each crossing through the real edge.
    """

    def test_a_template_is_filed_under_the_creators_organization(self, second_organization: tuple[APIClient, str]) -> None:
        client, organization_id = second_organization
        template_id = _create_template(client, "Созвездие — диплом")

        stored = TemplateModel.objects.get(id=template_id)
        assert str(stored.organizer_id) == organization_id

    def test_the_library_shows_only_the_callers_own(self, first_organization: APIClient, second_organization: tuple[APIClient, str]) -> None:
        client, _ = second_organization
        _create_template(first_organization, "Взлёт — диплом")
        _create_template(client, "Созвездие — диплом")

        first_names = [row["name"] for row in first_organization.get(_TEMPLATES).data["data"]]
        second_names = [row["name"] for row in client.get(_TEMPLATES).data["data"]]

        assert first_names == ["Взлёт — диплом"]
        assert second_names == ["Созвездие — диплом"]

    def test_reading_another_organizations_layout_is_refused(self, first_organization: APIClient, second_organization: tuple[APIClient, str]) -> None:
        client, _ = second_organization
        theirs = _create_template(first_organization, "Взлёт — диплом")

        assert client.get(f"{_TEMPLATES}/{theirs}/layout").status_code == 403

    def test_overwriting_another_organizations_layout_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        """The write, which is worse than the read: it would replace their design."""
        client, _ = second_organization
        theirs = _create_template(first_organization, "Взлёт — диплом")

        response = client.put(
            f"{_TEMPLATES}/{theirs}/layout",
            {"fields": [{"page": 1, "type": "participant_name", "x": 0.1, "y": 0.1, "width": 0.4, "height": 0.08}]},
            format="json",
        )

        assert response.status_code == 403
        # And nothing was written: the layout they own is still empty.
        assert first_organization.get(f"{_TEMPLATES}/{theirs}/layout").data["data"]["fields"] == []

    def test_uploading_a_pdf_onto_another_organizations_template_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_template(first_organization, "Взлёт — диплом")

        response = client.post(
            f"{_TEMPLATES}/{theirs}/document",
            {"file": SimpleUploadedFile("bg.pdf", b"%PDF-1.4 not really", content_type="application/pdf")},
            format="multipart",
        )

        assert response.status_code == 403
        # Refused *before* the upload, so nothing of theirs was replaced either.
        assert TemplateDocumentModel.objects.filter(template_id=uuid.UUID(theirs)).count() == 0


class TestDiplomaAssignmentsAreScopedToTheirOrganization:
    def test_the_list_shows_only_the_callers_own(self, first_organization: APIClient, second_organization: tuple[APIClient, str]) -> None:
        """And in particular does not leak the other side's competition title.

        An assignment row resolves its competition's title and its nomination's name
        into the response, so an unscoped listing hands over labels as well as ids.
        """
        client, _ = second_organization
        their_competition = _create_competition(first_organization, "Взлёт — сезон")
        their_nomination = _create_nomination(first_organization, their_competition)
        their_template = _create_template(first_organization, "Взлёт — диплом")
        assert (
            first_organization.post(
                _ASSIGNMENTS,
                {"competitionId": their_competition, "categoryIds": [their_nomination], "templateId": their_template},
                format="json",
            ).status_code
            == 201
        )

        rows = client.get(_ASSIGNMENTS).data["data"]

        assert rows == []

    def test_assigning_another_organizations_template_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_template(first_organization, "Взлёт — диплом")
        mine = _create_competition(client, "Созвездие — сезон")
        my_nomination = _create_nomination(client, mine)

        response = client.post(
            _ASSIGNMENTS,
            {"competitionId": mine, "categoryIds": [my_nomination], "templateId": theirs},
            format="json",
        )

        assert response.status_code == 403
        assert AssignmentModel.objects.count() == 0

    def test_assigning_onto_another_organizations_competition_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        """The mirror image: my own design, their festival."""
        client, _ = second_organization
        their_competition = _create_competition(first_organization, "Взлёт — сезон")
        their_nomination = _create_nomination(first_organization, their_competition)
        mine = _create_template(client, "Созвездие — диплом")

        response = client.post(
            _ASSIGNMENTS,
            {"competitionId": their_competition, "categoryIds": [their_nomination], "templateId": mine},
            format="json",
        )

        assert response.status_code == 403
        assert AssignmentModel.objects.count() == 0


class TestDiplomaPaperworkStopsAtTheCompetitionBoundary:
    """The endpoints that take a ``competitionId`` and used to trust it."""

    def test_the_registry_refuses_another_organizations_competition(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        assert client.get(f"{_REGISTRY}?competitionId={theirs}").status_code == 403

    def test_the_print_package_refuses_another_organizations_competition(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        assert client.get(f"/api/v1/staff/diplomas/print-package/summary?competitionId={theirs}").status_code == 403

    def test_the_generation_archive_refuses_another_organizations_competition(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        assert client.get(f"{_GENERATION_ARCHIVE}?competitionId={theirs}").status_code == 403

    def test_generating_documents_for_another_organization_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        """The worst of the crossings: this one *delivers*.

        `publish` defaults to true, so a successful call would put documents into the
        participants' cabinets of a festival the caller has nothing to do with.
        """
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")
        nomination = _create_nomination(first_organization, theirs)

        response = client.post(
            "/api/v1/staff/diplomas/documents/generate",
            {"competitionId": theirs, "categoryIds": [nomination], "documentType": "THANK_YOU"},
            format="json",
        )

        assert response.status_code == 403

    def test_starting_a_print_package_for_another_organization_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        response = client.post("/api/v1/staff/diplomas/print-package", {"competitionId": theirs}, format="json")

        assert response.status_code == 403
        assert PrintJobModel.objects.count() == 0

    def test_polling_another_organizations_print_job_is_refused(
        self, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        """A job carries no owner of its own — it names a competition, and that decides.

        The row is created through the ORM: what is under test is the guard on the
        way in, not the machinery that would have produced the job.
        """
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")
        job = PrintJobModel.objects.create(competition_id=uuid.UUID(theirs))

        assert client.get(f"/api/v1/staff/diplomas/print-package/{job.id}").status_code == 403
        # And the owner still reaches it, so the guard narrows rather than blocks.
        assert first_organization.get(f"/api/v1/staff/diplomas/print-package/{job.id}").status_code == 200

    def test_the_unfiltered_archive_is_still_scoped(self, first_organization: APIClient, second_organization: tuple[APIClient, str]) -> None:
        """The dangerous call: ``competitionId`` is optional on this endpoint.

        Omitted, it means "the whole history" — which without a scope is every
        organization's. The refusals above would all pass while this one leaked.
        """
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")
        GenerationRunModel.objects.create(competition_id=uuid.UUID(theirs), document_type="DIPLOMA", document_count=1)

        assert client.get(_GENERATION_ARCHIVE).data["data"] == []
        assert len(first_organization.get(_GENERATION_ARCHIVE).data["data"]) == 1


class TestThePlatformOperatorReadsEveryLibrary:
    """The deliberate exception, and the one place it differs from Competitions.

    ``TestCompetitionsAreScopedToTheirOrganization`` above asserts the operator is
    *refused* by the organizer API and reads through the platform console instead.
    The Diplomas surface admits them (``IsOrganizationStaff | IsPlatformAdministrator``)
    because there is no console equivalent for a template library. The two contexts
    therefore answer the operator differently on purpose; if that is ever unified,
    this class and the competitions one move together.
    """

    def test_the_operator_lists_every_organizations_templates(
        self, operator: APIClient, first_organization: APIClient, second_organization: tuple[APIClient, str]
    ) -> None:
        client, _ = second_organization
        _create_template(first_organization, "Взлёт — диплом")
        _create_template(client, "Созвездие — диплом")

        names = [row["name"] for row in operator.get(_TEMPLATES).data["data"]]

        assert {"Взлёт — диплом", "Созвездие — диплом"} <= set(names)

    def test_the_operator_authors_nothing_of_their_own(self, operator: APIClient) -> None:
        """Reading across organizations and writing into one are different rights.

        The operator is staff of no organization, so there is no library for a
        template of theirs to land in. Refusing says so; inventing an owner would
        put a row in somebody else's library.
        """
        response = operator.post(_TEMPLATES, {"name": "Ничей шаблон", "type": "DIPLOMA"}, format="json")

        assert response.status_code == 403
        assert TemplateModel.objects.count() == 0
