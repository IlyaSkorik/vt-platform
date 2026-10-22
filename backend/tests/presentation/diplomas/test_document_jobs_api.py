"""Integration tests for the document-generation job surface.

Generating a genre's thank-you letters renders a PDF per recipient and uploads a
ZIP. A festival-sized run takes minutes, which is longer than anything between
the organizer and the worker will hold a connection open — nginx answered 504
while the worker went on to finish, so the letters existed and the organizer was
told they did not. The run is therefore a job: the request queues it and hands
back something to poll.

Driven through DRF's ``APIClient`` because that is where the change lives — the
run itself is covered by the generation suites. Celery is eager in tests, so a
queued job is already finished by the time the response is written; what these
check is the *shape* of the exchange, not its timing.
"""

from __future__ import annotations

import io
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.infrastructure.models import DocumentJobModel, IssuedDocumentModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.diplomas.presentation.scope import Scope
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_GENERATE = "/api/v1/staff/diplomas/documents/generate"
_JOBS = "/api/v1/staff/diplomas/documents/jobs"


def _organizer() -> uuid.UUID:
    """The seeded organization the staff fixture below owns."""
    return uuid.UUID(str(OrganizationModel.objects.values_list("id", flat=True).get(slug="vzlyot-talantov")))


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "organizer@example.com", "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    # Minted directly: the login gate refuses unverified accounts, and these tests
    # need an authenticated caller rather than the verify flow.
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    build_provision_owner_handler().handle(
        ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]
    )
    return client


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    page.drawString(50, 50, "background")
    page.save()
    return buffer.getvalue()


def _thank_you_template() -> TemplateModel:
    template = TemplateModel.objects.create(organizer_id=_organizer(), type="THANK_YOU", name="Благодарность")
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    composition.replace_template_layout(
        template_id=str(template.id),
        fields=[
            {
                "page": 1,
                "type": "teacher",
                "binding": "teacher.display_name",
                "x": 0.1,
                "y": 0.1,
                "width": 0.6,
                "height": 0.1,
            }
        ],
    )
    return template


def _competition() -> tuple[CompetitionModel, CategoryModel]:
    """A competition with one genre and one accepted entry naming one teacher."""
    competition = CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=_organizer(),
        status="PUBLISHED",
        venue_name="Москва",
        competition_start=date(2026, 5, 15),
    )
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1}],
        teachers=[{"first_name": "Мария", "last_name": "Сидорова", "role": "Педагог"}],
        performance={"title": "Этюд", "nomination_id": str(vocals.id)},
    )
    return competition, vocals


def _start(client: APIClient, competition: CompetitionModel, category: CategoryModel, **body: Any) -> Response:
    return client.post(
        _GENERATE,
        {
            "competitionId": str(competition.id),
            "categoryIds": [str(category.id)],
            "documentType": "THANK_YOU",
            **body,
        },
        format="json",
    )


class TestQueueing:
    def test_the_request_answers_with_a_job_rather_than_the_run(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        composition.create_assignment(
            competition_id=str(competition.id),
            category_id=str(vocals.id),
            template_id=str(_thank_you_template().id),
            scope=Scope.for_organization(_organizer()),
        )

        response = _start(staff_client, competition, vocals, bundle=True)

        # 202, not 200: what came back is an acknowledgement, not the outcome.
        assert response.status_code == 202
        job = response.data["data"]
        assert job["documentType"] == "THANK_YOU"
        assert job["categoryIds"] == [str(vocals.id)]
        assert job["bundle"] is True
        assert DocumentJobModel.objects.get(id=job["jobId"]).competition_id == competition.id

    def test_a_finished_job_carries_the_run_s_own_summary(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        composition.create_assignment(
            competition_id=str(competition.id),
            category_id=str(vocals.id),
            template_id=str(_thank_you_template().id),
            scope=Scope.for_organization(_organizer()),
        )
        job_id = _start(staff_client, competition, vocals, bundle=True).data["data"]["jobId"]

        polled = staff_client.get(f"{_JOBS}/{job_id}")

        assert polled.status_code == 200
        job = polled.data["data"]
        assert job["status"] == "COMPLETED"
        assert job["error"] is None
        # The very object the endpoint used to answer with, so the page that renders
        # a finished run reads the same shape — only later.
        assert job["result"]["created"] == 1
        assert job["result"]["documents"] == 1
        assert job["result"]["zipUrl"].endswith("/ThankYou.zip")
        assert IssuedDocumentModel.objects.count() == 1

    def test_a_run_that_cannot_start_fails_the_job_rather_than_the_request(self, staff_client: APIClient) -> None:
        """A genre with no template of the kind is the worker's to report.

        It used to be the request's, because the run was the request. Now the
        only thing lost by queueing first is the immediate refusal — and the job
        carries the same sentence, so nothing about *what* the organizer is told
        changed.
        """
        competition, vocals = _competition()

        response = _start(staff_client, competition, vocals)

        assert response.status_code == 202
        job = staff_client.get(f"{_JOBS}/{response.data['data']['jobId']}").data["data"]
        assert job["status"] == "FAILED"
        assert job["error"] == "Для этого жанра не назначен шаблон такого типа."
        assert job["result"] is None
        assert IssuedDocumentModel.objects.count() == 0

    def test_a_diploma_is_still_refused_outright(self, staff_client: APIClient) -> None:
        """The one refusal worth keeping in the request.

        A numbered kind belongs to the print package, which reserves its numbers.
        The caller can still be told; a queued job could only die.
        """
        competition, vocals = _competition()

        response = _start(staff_client, competition, vocals, documentType="DIPLOMA")

        assert response.status_code == 400
        assert DocumentJobModel.objects.count() == 0


class TestPolling:
    def test_an_unknown_job_is_not_found(self, staff_client: APIClient) -> None:
        assert staff_client.get(f"{_JOBS}/{uuid.uuid4()}").status_code == 404

    def test_a_malformed_id_is_not_found_either(self, staff_client: APIClient) -> None:
        # Not a validation failure: the path segment is an id or it is nothing.
        assert staff_client.get(f"{_JOBS}/not-a-uuid").status_code == 404
