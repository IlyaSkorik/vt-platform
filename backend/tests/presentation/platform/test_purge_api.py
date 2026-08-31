"""Integration tests for the operator's eraser.

This is the one endpoint on the platform that destroys real data and cannot be
undone, so the properties worth pinning down are the ones that bound it rather
than the happy path alone: only the operator reaches it, the plan it shows is the
plan it executes, a mistyped confirmation changes nothing, and — the one that
matters most — each target stops exactly where it is supposed to stop. A festival
must not take its organization with it, an order must not take its festival, and
an account must not take the festivals it once worked on.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import ApplicationModel, ApplicationRevisionModel, SubmissionModel
from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel, DocumentModel
from apps.diplomas.infrastructure.models import AssignmentModel, DiplomaModel, TemplateModel
from apps.identity.infrastructure.models import UserModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.notifications.infrastructure.models import NotificationModel
from apps.organization.infrastructure.models import (
    MembershipStatusChoices,
    OrganizationModel,
    StaffMembershipModel,
    StaffRoleChoices,
)
from apps.participants.infrastructure.models import ParticipantRegistryModel
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler
from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel
from apps.results.infrastructure.models import ProtocolModel, ProtocolRowModel
from apps.teachers.infrastructure.models import TeacherModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_PURGE = "/api/v1/platform/purge"


# ----------------------------------------------------------------------
# Callers
# ----------------------------------------------------------------------


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
    client.operator_id = user_id  # type: ignore[attr-defined]  # carried for the self-deletion test
    return client


@pytest.fixture
def outsider() -> APIClient:
    """A registered account with no platform grant — an organization's OWNER is one."""
    client = APIClient()
    _register(client, "outsider@example.com")
    return client


@pytest.fixture
def _media_root(settings, tmp_path) -> None:  # type: ignore[no-untyped-def]  # pytest-django fixtures
    settings.MEDIA_ROOT = str(tmp_path)


# ----------------------------------------------------------------------
# A festival with something in every table the eraser reaches
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Festival:
    """One built festival, and handles on the rows the assertions care about."""

    organization: OrganizationModel
    competition: CompetitionModel
    applicant: UserModel
    application: ApplicationModel
    submission: SubmissionModel
    diploma: DiplomaModel
    program: ProgramModel
    item: ProgramItemModel
    protocol: ProtocolModel
    template: TemplateModel
    files: list[str]


def _stored(name: str) -> str:
    """A real file in storage, and the ``/media/…`` reference a row would hold."""
    return f"/media/{default_storage.save(name, ContentFile(b'x'))}"


def _account(email: str, *, last_name: str = "Иванова") -> UserModel:
    return UserModel.objects.create(
        email=email,
        first_name="Мария",
        last_name=last_name,
        locale="ru",
        timezone="Europe/Minsk",
        password_algorithm="argon2",
        password_hash="x",
    )


def _build_festival(*, title: str = "Взлёт талантов", email: str = "mother@example.com") -> Festival:
    """A festival carrying an order, a performance, a diploma, a programme and a protocol.

    Built through the models rather than through the API on purpose: the point of
    these tests is what the eraser reaches, and reaching it means having a row in
    every table it touches, including the ones no single API call would fill.
    """
    organization = OrganizationModel.objects.create(name=f"Дом культуры «{title}»", slug=f"dk-{uuid.uuid4().hex[:8]}")
    files = [_stored("competitions/logo.png"), _stored("competitions/regulation.pdf")]
    competition = CompetitionModel.objects.create(
        title=title,
        season="2026",
        organizer_id=organization.id,
        status="PUBLISHED",
        logo=files[0],
    )
    CategoryModel.objects.create(competition=competition, name="Вокал")
    DocumentModel.objects.create(
        competition=competition,
        title="Положение",
        category="REGULATION",
        visibility="PUBLIC",
        file_reference=files[1],
    )

    applicant = _account(email)
    attachment = _stored("submissions/track.mp3")
    receipt = _stored("receipts/slip.pdf")
    files += [attachment, receipt]
    submission = SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=applicant.id,
        status="SUBMITTED",
        attachments=[{"id": str(uuid.uuid4()), "type": "MUSIC", "file": attachment}],
    )
    application = ApplicationModel.objects.create(
        competition_id=competition.id,
        applicant_id=applicant.id,
        status="PAID",
        submission_refs=[{"submission_id": str(submission.id), "status": "SUBMITTED"}],
        payment_receipts=[{"id": str(uuid.uuid4()), "file_reference": receipt}],
    )
    ApplicationRevisionModel.objects.create(
        application_id=application.id,
        competition_id=competition.id,
        applicant_id=applicant.id,
        change="Заявка подана",
    )

    template = TemplateModel.objects.create(organizer_id=organization.id, type="DIPLOMA", name="Диплом")
    AssignmentModel.objects.create(
        competition_id=competition.id,
        category_id=uuid.uuid4(),
        template=template,
        document_type="DIPLOMA",
    )
    diploma_pdf = _stored("diplomas/print.pdf")
    files.append(diploma_pdf)
    diploma = DiplomaModel.objects.create(
        number=f"VT-2026-{uuid.uuid4().hex[:6]}",
        verification_token=uuid.uuid4().hex,
        competition_id=competition.id,
        submission_id=submission.id,
        template_id=template.id,
        print_pdf_path=diploma_pdf,
    )

    program = ProgramModel.objects.create(competition_id=competition.id, name="День первый")
    item = ProgramItemModel.objects.create(
        program=program,
        kind="PERFORMANCE",
        duration_seconds=180,
        submission_id=submission.id,
        number=1,
    )
    protocol = ProtocolModel.objects.create(competition_id=competition.id, nomination_id=uuid.uuid4(), name="Вокал")
    ProtocolRowModel.objects.create(protocol=protocol, submission_id=submission.id, number=1)

    return Festival(
        organization=organization,
        competition=competition,
        applicant=applicant,
        application=application,
        submission=submission,
        diploma=diploma,
        program=program,
        item=item,
        protocol=protocol,
        template=template,
        files=files,
    )


def _plan(client: APIClient, kind: str, object_id: object) -> dict:
    response = client.get(f"{_PURGE}/{kind}/{object_id}")
    assert response.status_code == 200, response.data
    return dict(response.data["data"])


def _erase(client: APIClient, kind: str, object_id: object, confirm: str):  # type: ignore[no-untyped-def]  # DRF response
    return client.delete(f"{_PURGE}/{kind}/{object_id}?confirm={confirm}")


def _row(plan: dict, table: str) -> int:
    """How many rows the plan reports for one table — zero when it names none."""
    return next((row["count"] for row in plan["rows"] if row["table"] == table), 0)


# ----------------------------------------------------------------------
# Who may reach it
# ----------------------------------------------------------------------


def test_the_eraser_is_closed_to_everyone_but_the_operator(outsider: APIClient) -> None:
    festival = _build_festival()

    assert outsider.get(f"{_PURGE}/search?target=festival&query=Взлёт").status_code == 403
    assert outsider.get(f"{_PURGE}/festival/{festival.competition.id}").status_code == 403
    assert _erase(outsider, "festival", festival.competition.id, festival.competition.title).status_code == 403
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()


def test_an_anonymous_caller_gets_nothing() -> None:
    festival = _build_festival()

    response = APIClient().delete(f"{_PURGE}/festival/{festival.competition.id}?confirm={festival.competition.title}")

    assert response.status_code in {401, 403}
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()


# ----------------------------------------------------------------------
# The plan
# ----------------------------------------------------------------------


def test_the_plan_names_every_table_and_changes_nothing(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()

    plan = _plan(operator, "festival", festival.competition.id)

    assert plan["target"]["label"] == festival.competition.title
    assert _row(plan, "competitions_competition") == 1
    assert _row(plan, "competitions_category") == 1
    assert _row(plan, "applications_application") == 1
    assert _row(plan, "applications_submission") == 1
    assert _row(plan, "diplomas_diploma") == 1
    assert _row(plan, "programs_program") == 1
    assert _row(plan, "results_protocol") == 1
    assert plan["files"] == len(festival.files)
    assert plan["total"] >= 7
    assert plan["warnings"]
    # Reading the plan is a read: nothing above may have gone.
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert SubmissionModel.objects.filter(id=festival.submission.id).exists()


def test_the_plan_never_reaches_above_the_festival(operator: APIClient) -> None:
    """Its organization, that organization's staff and its templates are not in it."""
    festival = _build_festival()

    plan = _plan(operator, "festival", festival.competition.id)

    assert _row(plan, "organization_organization") == 0
    assert _row(plan, "identity_user") == 0
    assert _row(plan, "diplomas_template") == 0


# ----------------------------------------------------------------------
# Erasing a festival
# ----------------------------------------------------------------------


def test_erasing_a_festival_takes_its_whole_tree(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()

    response = _erase(operator, "festival", festival.competition.id, festival.competition.title)

    assert response.status_code == 200, response.data
    assert not CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert not CategoryModel.objects.filter(competition_id=festival.competition.id).exists()
    assert not ApplicationModel.objects.filter(id=festival.application.id).exists()
    assert not ApplicationRevisionModel.objects.filter(competition_id=festival.competition.id).exists()
    assert not SubmissionModel.objects.filter(id=festival.submission.id).exists()
    assert not DiplomaModel.objects.filter(id=festival.diploma.id).exists()
    assert not AssignmentModel.objects.filter(competition_id=festival.competition.id).exists()
    assert not ProgramModel.objects.filter(id=festival.program.id).exists()
    assert not ProgramItemModel.objects.filter(id=festival.item.id).exists()
    assert not ProtocolModel.objects.filter(id=festival.protocol.id).exists()
    assert not ProtocolRowModel.objects.filter(protocol_id=festival.protocol.id).exists()


def test_erasing_a_festival_frees_the_disk_it_was_using(operator: APIClient, _media_root: None) -> None:
    """The point of a hard delete: the bytes go, not just the rows pointing at them."""
    festival = _build_festival()
    assert all(default_storage.exists(reference.removeprefix("/media/")) for reference in festival.files)

    response = _erase(operator, "festival", festival.competition.id, festival.competition.title)

    assert response.data["data"]["files"] == len(festival.files)
    assert not any(default_storage.exists(reference.removeprefix("/media/")) for reference in festival.files)


def test_erasing_a_festival_leaves_its_organization_standing(operator: APIClient, _media_root: None) -> None:
    """A festival is one season; the organization that ran it outlives it."""
    festival = _build_festival()
    neighbour = _build_festival(title="Соседний фестиваль", email="neighbour@example.com")

    _erase(operator, "festival", festival.competition.id, festival.competition.title)

    assert OrganizationModel.objects.filter(id=festival.organization.id).exists()
    assert TemplateModel.objects.filter(id=festival.template.id).exists()
    assert UserModel.objects.filter(id=festival.applicant.id).exists()
    assert CompetitionModel.objects.filter(id=neighbour.competition.id).exists()
    assert SubmissionModel.objects.filter(id=neighbour.submission.id).exists()


def test_the_report_counts_what_went_rather_than_what_is_left(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()
    planned = _plan(operator, "festival", festival.competition.id)

    response = _erase(operator, "festival", festival.competition.id, festival.competition.title)

    assert response.data["data"]["total"] == planned["total"]
    assert response.data["data"]["files"] == planned["files"]


# ----------------------------------------------------------------------
# The confirmation
# ----------------------------------------------------------------------


def test_a_mistyped_confirmation_deletes_nothing(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()

    response = _erase(operator, "festival", festival.competition.id, "Не тот фестиваль")

    assert response.status_code == 400, response.data
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert SubmissionModel.objects.filter(id=festival.submission.id).exists()
    assert all(default_storage.exists(reference.removeprefix("/media/")) for reference in festival.files)


def test_a_missing_confirmation_deletes_nothing(operator: APIClient) -> None:
    festival = _build_festival()

    response = operator.delete(f"{_PURGE}/festival/{festival.competition.id}")

    assert response.status_code == 400, response.data
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()


def test_the_confirmation_forgives_case_and_spacing_and_nothing_else(operator: APIClient, _media_root: None) -> None:
    """Retyping a title is the guard; punishing a stray space would only teach copy-paste."""
    festival = _build_festival()

    response = _erase(operator, "festival", festival.competition.id, f"  {festival.competition.title.upper()}  ")

    assert response.status_code == 200, response.data
    assert not CompetitionModel.objects.filter(id=festival.competition.id).exists()


# ----------------------------------------------------------------------
# Erasing one order
# ----------------------------------------------------------------------


def test_erasing_an_order_leaves_the_festival_standing(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()
    other = SubmissionModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=_account("second@example.com").id,
        status="SUBMITTED",
    )

    response = _erase(operator, "application", festival.application.id, festival.applicant.email)

    assert response.status_code == 200, response.data
    assert not ApplicationModel.objects.filter(id=festival.application.id).exists()
    assert not SubmissionModel.objects.filter(id=festival.submission.id).exists()
    assert not DiplomaModel.objects.filter(id=festival.diploma.id).exists()
    # The festival, its taxonomy, its programme and somebody else's performance stay.
    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert CategoryModel.objects.filter(competition_id=festival.competition.id).exists()
    assert ProgramModel.objects.filter(id=festival.program.id).exists()
    assert ProtocolModel.objects.filter(id=festival.protocol.id).exists()
    assert SubmissionModel.objects.filter(id=other.id).exists()


def test_erasing_an_order_pulls_its_acts_out_of_the_running_order(operator: APIClient, _media_root: None) -> None:
    """A programme must not keep a slot for a performance that no longer exists."""
    festival = _build_festival()

    _erase(operator, "application", festival.application.id, festival.applicant.email)

    assert not ProgramItemModel.objects.filter(id=festival.item.id).exists()
    assert not ProtocolRowModel.objects.filter(submission_id=festival.submission.id).exists()


def test_erasing_an_order_leaves_a_second_order_by_the_same_person(operator: APIClient, _media_root: None) -> None:
    """Scoped to the order's own list of acts, not to everything that applicant sent."""
    festival = _build_festival()
    second_submission = SubmissionModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=festival.applicant.id,
        status="SUBMITTED",
    )
    second_order = ApplicationModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=festival.applicant.id,
        status="DRAFT",
        submission_refs=[{"submission_id": str(second_submission.id), "status": "DRAFT"}],
    )

    _erase(operator, "application", festival.application.id, festival.applicant.email)

    assert ApplicationModel.objects.filter(id=second_order.id).exists()
    assert SubmissionModel.objects.filter(id=second_submission.id).exists()


# ----------------------------------------------------------------------
# Erasing an organization
# ----------------------------------------------------------------------


def test_erasing_an_organization_takes_its_festivals_and_templates(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()
    membership = StaffMembershipModel.objects.create(
        organization_id=festival.organization.id,
        user_id=festival.applicant.id,
        role=StaffRoleChoices.OWNER,
        status=MembershipStatusChoices.ACTIVE,
    )

    response = _erase(operator, "organization", festival.organization.id, festival.organization.name)

    assert response.status_code == 200, response.data
    assert not OrganizationModel.objects.filter(id=festival.organization.id).exists()
    assert not CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert not TemplateModel.objects.filter(id=festival.template.id).exists()
    assert not StaffMembershipModel.objects.filter(id=membership.id).exists()
    assert not SubmissionModel.objects.filter(id=festival.submission.id).exists()


def test_erasing_an_organization_leaves_the_people_who_worked_there(operator: APIClient, _media_root: None) -> None:
    """A person is not owned by the organization they work for."""
    festival = _build_festival()
    StaffMembershipModel.objects.create(
        organization_id=festival.organization.id,
        user_id=festival.applicant.id,
        role=StaffRoleChoices.OWNER,
        status=MembershipStatusChoices.ACTIVE,
    )

    _erase(operator, "organization", festival.organization.id, festival.organization.name)

    assert UserModel.objects.filter(id=festival.applicant.id).exists()


# ----------------------------------------------------------------------
# Erasing an account
# ----------------------------------------------------------------------


def test_erasing_an_account_takes_what_was_entered_under_it(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()
    avatar = _stored("participants/avatars/face.jpg")
    participant = ParticipantRegistryModel.objects.create(
        owner_id=festival.applicant.id,
        first_name="Аня",
        last_name="Иванова",
        birth_date=date(2012, 5, 1),
        gender="FEMALE",
        avatar_url=avatar,
    )
    teacher = TeacherModel.objects.create(
        owner_id=festival.applicant.id,
        first_name="Ольга",
        last_name="Петрова",
        role="TEACHER",
        status="ACTIVE",
    )
    notification = NotificationModel.objects.create(
        recipient_id=festival.applicant.id,
        kind="APPLICATION_SUBMITTED",
        title="Заявка подана",
    )

    response = _erase(operator, "account", festival.applicant.id, festival.applicant.email)

    assert response.status_code == 200, response.data
    assert not UserModel.objects.filter(id=festival.applicant.id).exists()
    assert not ParticipantRegistryModel.objects.filter(id=participant.id).exists()
    assert not TeacherModel.objects.filter(id=teacher.id).exists()
    assert not NotificationModel.objects.filter(id=notification.id).exists()
    assert not ApplicationModel.objects.filter(id=festival.application.id).exists()
    assert not SubmissionModel.objects.filter(id=festival.submission.id).exists()
    assert not default_storage.exists(avatar.removeprefix("/media/"))


def test_erasing_an_account_leaves_the_festival_it_applied_to(operator: APIClient, _media_root: None) -> None:
    festival = _build_festival()

    _erase(operator, "account", festival.applicant.id, festival.applicant.email)

    assert CompetitionModel.objects.filter(id=festival.competition.id).exists()
    assert OrganizationModel.objects.filter(id=festival.organization.id).exists()
    assert ProgramModel.objects.filter(id=festival.program.id).exists()


def test_the_operator_cannot_erase_the_account_they_are_working_from(operator: APIClient) -> None:
    """A console that can lock itself out mid-operation is a console with no way back."""
    operator_id = operator.operator_id  # type: ignore[attr-defined]
    email = UserModel.objects.get(id=operator_id).email

    response = _erase(operator, "account", operator_id, email)

    assert response.status_code == 409, response.data
    assert UserModel.objects.filter(id=operator_id).exists()


def test_the_plan_warns_when_an_organization_would_lose_its_last_owner(operator: APIClient) -> None:
    festival = _build_festival()
    StaffMembershipModel.objects.create(
        organization_id=festival.organization.id,
        user_id=festival.applicant.id,
        role=StaffRoleChoices.OWNER,
        status=MembershipStatusChoices.ACTIVE,
    )

    plan = _plan(operator, "account", festival.applicant.id)

    assert any(festival.organization.name in warning for warning in plan["warnings"])


# ----------------------------------------------------------------------
# Erasing a registry card
# ----------------------------------------------------------------------


def test_a_registry_card_goes_without_rewriting_what_was_already_sent(operator: APIClient, _media_root: None) -> None:
    """A sent performance carries its own copy of the name — that copy is the record."""
    festival = _build_festival()
    participant = ParticipantRegistryModel.objects.create(
        owner_id=festival.applicant.id,
        first_name="Аня",
        last_name="Иванова",
        birth_date=date(2012, 5, 1),
        gender="FEMALE",
    )
    festival.submission.participants = [{"id": str(uuid.uuid4()), "display_name": "Аня Иванова"}]
    festival.submission.save(update_fields=["participants"])

    response = _erase(operator, "participant", participant.id, "Иванова Аня")

    assert response.status_code == 200, response.data
    assert not ParticipantRegistryModel.objects.filter(id=participant.id).exists()
    submission = SubmissionModel.objects.get(id=festival.submission.id)
    assert submission.participants[0]["display_name"] == "Аня Иванова"


def test_a_teacher_card_goes_on_its_own(operator: APIClient) -> None:
    owner = _account("teacher-owner@example.com")
    teacher = TeacherModel.objects.create(
        owner_id=owner.id,
        first_name="Ольга",
        last_name="Петрова",
        role="TEACHER",
        status="ACTIVE",
    )

    response = _erase(operator, "teacher", teacher.id, "Петрова Ольга")

    assert response.status_code == 200, response.data
    assert not TeacherModel.objects.filter(id=teacher.id).exists()
    assert UserModel.objects.filter(id=owner.id).exists()


# ----------------------------------------------------------------------
# Finding the thing, and being told when it is not there
# ----------------------------------------------------------------------


def test_search_finds_a_festival_by_name_and_by_id(operator: APIClient) -> None:
    festival = _build_festival()

    by_name = operator.get(f"{_PURGE}/search?target=festival&query=Взлёт")
    by_id = operator.get(f"{_PURGE}/search?target=festival&query={festival.competition.id}")

    assert [row["id"] for row in by_name.data["data"]] == [str(festival.competition.id)]
    assert [row["id"] for row in by_id.data["data"]] == [str(festival.competition.id)]
    assert by_name.data["data"][0]["label"] == festival.competition.title


def test_search_finds_an_order_by_the_email_that_placed_it(operator: APIClient) -> None:
    festival = _build_festival()

    response = operator.get(f"{_PURGE}/search?target=application&query={festival.applicant.email}")

    assert [row["id"] for row in response.data["data"]] == [str(festival.application.id)]


def test_an_empty_query_finds_nothing_rather_than_everything(operator: APIClient) -> None:
    """A blank box must not turn a targeted tool into a browsable list of the database."""
    _build_festival()

    response = operator.get(f"{_PURGE}/search?target=festival&query=")

    assert response.status_code == 200
    assert response.data["data"] == []


def test_an_unknown_kind_or_a_missing_object_is_a_404(operator: APIClient) -> None:
    assert operator.get(f"{_PURGE}/search?target=galaxy&query=x").status_code == 404
    assert operator.get(f"{_PURGE}/festival/{uuid.uuid4()}").status_code == 404
    assert operator.get(f"{_PURGE}/festival/not-a-uuid").status_code == 404
    assert _erase(operator, "festival", uuid.uuid4(), "Что угодно").status_code == 404
