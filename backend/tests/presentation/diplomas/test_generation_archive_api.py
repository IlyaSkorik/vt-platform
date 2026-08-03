"""Integration tests for the generation archive (organizer-side history).

Driven through DRF's ``APIClient`` as organization staff, because the two things
the archive must get right only exist at the edge: *who* ran a generation (the
authenticated caller) and *that both mechanisms* land in one history — the diploma
package via its Celery task (eager in tests) and the thank-you runs inline.
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
from apps.diplomas.infrastructure.models import TemplateDocumentModel, TemplateModel
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ARCHIVE = "/api/v1/staff/diplomas/generation-archive"


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


def _authenticated(client: APIClient, email: str, *, first: str, last: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": first, "lastName": last},
        format="json",
    )
    # Mint the token directly: the login gate refuses unverified accounts, and these
    # tests need an authenticated caller rather than the verify flow.
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    """Staff whose name the archive is expected to show."""
    client = APIClient()
    access = _authenticated(client, "organizer@example.com", first="Ольга", last="Петрова")
    build_provision_owner_handler().handle(
        ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]
    )
    return client


@pytest.fixture
def participant_client() -> APIClient:
    """Authenticated, but not staff."""
    client = APIClient()
    _authenticated(client, "participant@example.com", first="Иван", last="Иванов")
    return client


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    page.drawString(50, 50, "background")
    page.save()
    return buffer.getvalue()


def _template(name: str, document_type: str) -> TemplateModel:
    template = TemplateModel.objects.create(type=document_type, name=name)
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    composition.replace_template_layout(
        template_id=str(template.id),
        fields=[
            {
                "page": 1,
                "type": "participant_name",
                "binding": "participant.display_name",
                "x": 0.1,
                "y": 0.1,
                "width": 0.6,
                "height": 0.1,
            }
        ],
    )
    return template


def _competition(title: str = "Восходящие таланты") -> tuple[CompetitionModel, CategoryModel]:
    """A competition with one nomination, one accepted entry naming one teacher."""
    competition = CompetitionModel.objects.create(
        title=title,
        season="2026",
        organizer_id=uuid.uuid4(),
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


def _assign(competition: CompetitionModel, category: CategoryModel, template: TemplateModel) -> None:
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
    )


def _generate_letters(client: APIClient, competition: CompetitionModel, category: CategoryModel, **body: Any) -> Response:
    return client.post(
        "/api/v1/staff/diplomas/documents/generate",
        {
            "competitionId": str(competition.id),
            "categoryIds": [str(category.id)],
            "documentType": "THANK_YOU",
            **body,
        },
        format="json",
    )


def _runs(client: APIClient, **params: str) -> list[dict[str, Any]]:
    response = client.get(_ARCHIVE, params or None)
    assert response.status_code == 200, response.data
    runs: list[dict[str, Any]] = response.data["data"]
    return runs


class TestHistory:
    def test_a_print_run_is_archived_with_its_author_and_its_zip(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))
        _generate_letters(staff_client, competition, vocals, bundle=True, publish=False)

        runs = _runs(staff_client)

        assert len(runs) == 1
        run = runs[0]
        assert run["documentType"] == "THANK_YOU"
        assert run["competition"] == "Восходящие таланты"
        assert (run["documents"], run["created"], run["published"]) == (1, 1, 0)
        assert run["nominations"] == 1
        # The two things only the edge knows: who asked, and where the ZIP is.
        assert run["user"] == "Петрова Ольга"
        assert str(run["zipUrl"]).endswith("ThankYou.zip")
        assert run["createdAt"]

    def test_a_publish_run_is_archived_with_nothing_to_download(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))
        _generate_letters(staff_client, competition, vocals)

        run = _runs(staff_client)[0]

        assert run["published"] == 1
        # A publish-only run printed nothing, so the archive offers no download
        # rather than a link to an archive that was never built.
        assert run["zipUrl"] is None

    def test_the_diploma_package_lands_in_the_same_history(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        started = staff_client.post(
            "/api/v1/staff/diplomas/print-package",
            {"competitionId": str(competition.id), "categoryIds": [str(vocals.id)]},
            format="json",
        )
        assert started.status_code == 202, started.data

        run = _runs(staff_client)[0]

        # One archive for both mechanisms — the organizer asks "what did we generate",
        # not "which of the two pipelines produced it".
        assert run["documentType"] == "DIPLOMA"
        assert (run["documents"], run["created"]) == (1, 1)
        assert run["user"] == "Петрова Ольга"
        assert str(run["zipUrl"]).endswith("Diplomas.zip")

    def test_every_run_is_kept_newest_first(self, staff_client: APIClient) -> None:
        competition, vocals = _competition()
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))
        _generate_letters(staff_client, competition, vocals, publish=False)
        _generate_letters(staff_client, competition, vocals, bundle=True)

        runs = _runs(staff_client)

        # A re-run is its own line: the archive is a history, not a current state.
        assert len(runs) == 2
        assert [run["published"] for run in runs] == [1, 0]

    def test_it_can_be_narrowed_to_one_competition(self, staff_client: APIClient) -> None:
        first, first_vocals = _competition("Первый фестиваль")
        second, second_vocals = _competition("Второй фестиваль")
        _assign(first, first_vocals, _template("Благодарность 1", "THANK_YOU"))
        _assign(second, second_vocals, _template("Благодарность 2", "THANK_YOU"))
        _generate_letters(staff_client, first, first_vocals)
        _generate_letters(staff_client, second, second_vocals)

        runs = _runs(staff_client, competitionId=str(second.id))

        assert [run["competition"] for run in runs] == ["Второй фестиваль"]

    def test_a_bad_competition_id_is_a_validation_problem(self, staff_client: APIClient) -> None:
        response = staff_client.get(_ARCHIVE, {"competitionId": "not-a-uuid"})

        assert response.status_code == 400

    def test_a_non_staff_caller_is_refused(self, participant_client: APIClient) -> None:
        assert participant_client.get(_ARCHIVE).status_code == 403
