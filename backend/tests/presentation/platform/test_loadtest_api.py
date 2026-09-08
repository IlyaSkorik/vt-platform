"""Integration tests for the operator's diploma-generation load test.

The endpoint is pointed at a live deployment, so the properties worth pinning down
are the ones that make that safe rather than the happy path alone: it is
operator-only, it seeds data generation actually consumes, it never advances the
real diploma numbering, and cleanup puts the database back the way it was without
taking anything real with it.
"""

from __future__ import annotations

import io
import uuid

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    DiplomaModel,
    DiplomaNumberSequenceModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.participants.infrastructure.models.registry import (
    EducationalOrganizationModel,
    ParticipantRegistryModel,
)
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler
from apps.platform.presentation.api.v1.loadtest import MARKER, SANDBOX_YEAR

pytestmark = pytest.mark.django_db

#: One organization for everything this module builds. A template and the
#: competition it is used on have to belong to the same organizer now — the scoped
#: listings admit a row only when both sides match — so a fresh `uuid4()` per
#: competition would put them on opposite sides of the boundary.
_ORGANIZER = uuid.UUID("00000000-0000-4000-8000-0000000000a1")


_PASSWORD = "V3ry$ecurePass!"
_LOADTEST = "/api/v1/platform/loadtest/diplomas"


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
    client = APIClient()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def organization_owner() -> APIClient:
    """An organization's OWNER — the top of *their* organization, and nothing here."""
    client = APIClient()
    user_id = _register(client, "owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


@pytest.fixture
def _media_root(settings, tmp_path) -> None:  # type: ignore[no-untyped-def]  # pytest-django fixtures
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def template(_media_root: None) -> TemplateModel:
    """A diploma template with a real one-page PDF and a single bound field."""
    from apps.diplomas.presentation.api.v1.diplomas import composition

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    page.drawString(50, 50, "background")
    page.save()

    row = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Нагрузочный шаблон")
    key = default_storage.save(f"diplomas/templates/{row.id}/bg.pdf", ContentFile(buffer.getvalue()))
    TemplateDocumentModel.objects.create(template=row, file_reference=f"/media/{key}", page_count=1)
    composition.replace_template_layout(
        template_id=str(row.id),
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
    return row


def test_operator_starts_a_run_and_generation_produces_every_diploma(operator: APIClient, template: TemplateModel) -> None:
    response = operator.post(_LOADTEST, {"count": 6, "nominations": 3}, format="json")

    assert response.status_code == 202, response.data
    run = response.data["data"]
    assert run["entries"] == 6
    assert run["nominations"] == 3
    assert len(run["jobs"]) == 1

    # CELERY_TASK_ALWAYS_EAGER in the test settings runs the job inline, so by the
    # time the request returns the package is already built.
    competition_id = run["competitionId"]
    assert DiplomaModel.objects.filter(competition_id=competition_id).count() == 6
    assert AssignmentModel.objects.filter(competition_id=competition_id).count() == 3

    overview = operator.get(_LOADTEST)
    assert overview.status_code == 200
    listed = overview.data["data"]["runs"][0]
    assert listed["status"] == "COMPLETED"
    assert listed["rendered"] == 6
    assert listed["jobs"][0]["zipUrl"]


def test_seeded_entries_fill_every_field_a_diploma_can_print(operator: APIClient, template: TemplateModel) -> None:
    """A blank field is a query that never ran — and a page that measures nothing.

    Every binding a diploma template offers is checked here, because each one costs
    the generator something (a taxonomy name lookup, the registry membership join)
    and a run that leaves them empty reports a speed production will never see. The
    award degree is the deliberate exception: a print-package copy is made before
    the ceremony, so it has no degree in production either.
    """
    response = operator.post(_LOADTEST, {"count": 2, "nominations": 1}, format="json")

    diploma = DiplomaModel.objects.filter(competition_id=response.data["data"]["competitionId"]).first()
    assert diploma is not None
    snapshot = diploma.snapshot
    assert snapshot["participant"]["display_name"]
    assert snapshot["participant"]["age"] is not None
    assert snapshot["teachers"] and snapshot["teachers"][0]["name"]
    assert snapshot["organization"]["name"]
    assert snapshot["nomination"]["title"]
    assert snapshot["nomination"]["discipline"]
    assert snapshot["nomination"]["participant_group"]
    assert snapshot["nomination"]["age_category"]
    assert snapshot["performance"]["title"]
    assert snapshot["competition"]["title"]
    assert snapshot["competition"]["date"]
    assert snapshot["competition"]["city"]
    assert snapshot["award"]["degree"] is None


def test_split_enqueues_one_job_per_nomination(operator: APIClient, template: TemplateModel) -> None:
    """The queue-pressure shape: several jobs competing, not one long one."""
    response = operator.post(_LOADTEST, {"count": 6, "nominations": 3, "split": True}, format="json")

    assert response.status_code == 202, response.data
    assert len(response.data["data"]["jobs"]) == 3


def test_a_run_never_advances_the_real_numbering(operator: APIClient, template: TemplateModel) -> None:
    """Diploma numbers are permanent — a test must not spend a real participant's."""
    DiplomaNumberSequenceModel.objects.create(scope="2026", current_number=41)

    response = operator.post(_LOADTEST, {"count": 3, "nominations": 1}, format="json")

    numbers = list(DiplomaModel.objects.filter(competition_id=response.data["data"]["competitionId"]).values_list("number", flat=True))
    assert numbers and all(number.startswith(f"VT-{SANDBOX_YEAR}-") for number in numbers), numbers
    assert DiplomaNumberSequenceModel.objects.get(scope="2026").current_number == 41


def test_cleanup_removes_the_run_and_leaves_real_data_alone(operator: APIClient, template: TemplateModel) -> None:
    real = CompetitionModel.objects.create(
        title="Настоящий фестиваль",
        season="2026",
        organizer_id=_ORGANIZER,
        status="PUBLISHED",
    )
    operator.post(_LOADTEST, {"count": 4, "nominations": 2}, format="json")

    response = operator.delete(_LOADTEST)

    assert response.status_code == 200, response.data
    assert response.data["data"]["runs"] == 1
    assert response.data["data"]["entries"] == 4
    assert not CompetitionModel.objects.filter(settings__load_test=MARKER).exists()
    assert not SubmissionModel.objects.exists()
    assert not DiplomaModel.objects.exists()
    assert not DiplomaNumberSequenceModel.objects.filter(scope=str(SANDBOX_YEAR)).exists()
    # The registry rows too — they live outside the competition and would otherwise
    # be orphaned, since nothing links them back to a run once it is gone.
    assert not ParticipantRegistryModel.objects.exists()
    assert not EducationalOrganizationModel.objects.exists()
    # The template it printed over, and anything that was never part of a run, survive.
    assert TemplateModel.objects.filter(id=template.id).exists()
    assert CompetitionModel.objects.filter(id=real.id).exists()


def test_cleanup_can_be_scoped_to_one_run(operator: APIClient, template: TemplateModel) -> None:
    first = operator.post(_LOADTEST, {"count": 2, "nominations": 1}, format="json").data["data"]["competitionId"]
    second = operator.post(_LOADTEST, {"count": 2, "nominations": 1}, format="json").data["data"]["competitionId"]

    response = operator.delete(f"{_LOADTEST}?competitionId={first}")

    assert response.status_code == 200
    assert response.data["data"]["runs"] == 1
    assert not CompetitionModel.objects.filter(id=first).exists()
    assert CompetitionModel.objects.filter(id=second).exists()
    # Still one run in flight, so the sandbox counter must survive — dropping it
    # would hand the next run numbers this one already issued.
    assert DiplomaNumberSequenceModel.objects.filter(scope=str(SANDBOX_YEAR)).exists()


def test_refused_without_a_printable_template(operator: APIClient, _media_root: None) -> None:
    TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон без PDF")

    response = operator.post(_LOADTEST, {"count": 2, "nominations": 1}, format="json")

    assert response.status_code == 400
    assert "шаблон" in response.data["detail"].lower()


def test_organization_owner_is_not_admitted(organization_owner: APIClient) -> None:
    assert organization_owner.get(_LOADTEST).status_code == 403
    assert organization_owner.post(_LOADTEST, {"count": 2}, format="json").status_code == 403
    assert organization_owner.delete(_LOADTEST).status_code == 403


def test_anonymous_is_not_admitted() -> None:
    assert APIClient().get(_LOADTEST).status_code == 401
