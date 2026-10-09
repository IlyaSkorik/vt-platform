"""Организатор забирает обратно свой же запрос на исправление.

Возврат на доработку передаёт ход участнику — и там он и остаётся: своей «подать
заново» у участника нет (подача заказа отправляет только черновики), а в статусе
REQUIRES_CORRECTION организатору не предлагалось ни одного действия. Запрос,
отправленный по ошибке или снятый по договорённости, парковал номер до конца
сезона: единственным выходом была замена квитанции (см. ``test_receipt_returns_to_review``),
то есть случайность, а не решение.

Эти тесты покрывают кнопку: статус, история, письмо участнику и отказ там, где
забирать нечего.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from django.core import mail
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.competitions.infrastructure.models.rules import AdmissionRuleModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.notifications.infrastructure.models import NotificationKind, NotificationModel
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_APPLICANT_EMAIL = "applicant@example.com"


def _register(client: APIClient, email: str, first_name: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": first_name, "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    access = _register(client, "organizer@example.com", "Ольга")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


@pytest.fixture
def applicant_id(staff_client: APIClient) -> uuid.UUID:
    """Настоящий пользователь Identity — письмо уходит на его сохранённый адрес."""
    client = APIClient()
    access = _register(client, _APPLICANT_EMAIL, "Мария")
    return uuid.UUID(str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]


class _Festival:
    """Фестиваль организации, принимающий ровно одно сочетание.

    Таксономия нужна целиком: вернуть номер в очередь — значит заново спросить
    у фестиваля, принимает ли он такое сочетание.
    """

    def __init__(self) -> None:
        organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
        assert organization_id is not None, "expected a provisioned organization"
        self.competition = CompetitionModel.objects.create(
            organizer_id=organization_id,
            status="PUBLISHED",
            title="Весенний фестиваль",
            season="2025/2026",
        )
        self.nomination = CategoryModel.objects.create(
            competition=self.competition,
            name="Вокал",
            registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
            registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
        )
        self.discipline = DisciplineModel.objects.create(competition=self.competition, category_id=self.nomination.id, name="Эстрадный вокал")
        self.group = ParticipantGroupModel.objects.create(competition=self.competition, name="Соло", min_count=1, max_count=1)
        self.age = AgeCategoryModel.objects.create(
            competition=self.competition, participant_group_id=self.group.id, name="7-9 лет", min_age=7, max_age=9
        )
        self.format = ParticipationFormatModel.objects.create(competition=self.competition, name="Очно")
        AdmissionRuleModel.objects.create(
            competition=self.competition,
            category_id=self.nomination.id,
            discipline_id=self.discipline.id,
            age_category_id=self.age.id,
            participant_group_id=self.group.id,
            participation_format_id=self.format.id,
        )

    def performance(self) -> dict[str, Any]:
        return {
            "title": "Лебединое озеро",
            "duration_seconds": 210,
            "nomination_id": str(self.nomination.id),
            "discipline_id": str(self.discipline.id),
            "age_category_id": str(self.age.id),
            "participant_group_id": str(self.group.id),
            "participation_format_id": str(self.format.id),
            "comment": "",
            "age_composition": "",
        }


def _returned_order(festival: _Festival, applicant_id: uuid.UUID, *, performances: int = 1) -> tuple[ApplicationModel, list[SubmissionModel]]:
    """Заказ, целиком возвращённый организатором на доработку."""
    submissions = [
        SubmissionModel.objects.create(
            competition_id=festival.competition.id,
            applicant_id=applicant_id,
            status="REQUIRES_CORRECTION",
            performance=festival.performance(),
            participants=[
                {
                    "id": str(uuid7()),
                    "display_name": "Иванова Анна",
                    "first_name": "Анна",
                    "last_name": "Иванова",
                    "middle_name": None,
                    "birth_date": "2018-05-12",
                    "gender": "FEMALE",
                    "registry_participant_id": None,
                    "member_count": 1,
                    "members": [],
                }
            ],
            teachers=[
                {
                    "id": str(uuid7()),
                    "first_name": "Ольга",
                    "last_name": "Петрова",
                    "middle_name": None,
                    "role": "Педагог",
                    "directory_teacher_id": None,
                }
            ],
            price_snapshot={"amount": "1500.00", "currency": "BYN", "calculated_at": "2026-07-10T00:00:00+00:00"},
        )
        for _ in range(performances)
    ]
    application = ApplicationModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status="SUBMITTED",
        submission_refs=[
            {"submission_id": str(s.id), "participant_display_name": "Иванова Анна", "status": "REQUIRES_CORRECTION"} for s in submissions
        ],
    )
    return application, submissions


def _withdraw(client: APIClient, submission_id: uuid.UUID, comment: str = "") -> Any:
    payload = {"comment": comment} if comment else {}
    return client.post(f"/api/v1/staff/applications/{submission_id}/actions/withdraw_correction_request", payload, format="json")


class TestTheRequestCanBeTakenBack:
    def test_the_entry_goes_back_into_the_queue(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)

        response = _withdraw(staff_client, submissions[0].id)

        assert response.status_code == 200, response.data
        assert response.data["data"]["status"] == "SUBMITTED"
        submissions[0].refresh_from_db()
        assert submissions[0].status == "SUBMITTED"

    def test_it_reaches_every_entry_the_return_reached(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # Возврат уходил одним кликом на весь заказ; забирать его по номеру —
        # уже другая операция.
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id, performances=3)

        _withdraw(staff_client, submissions[0].id)

        for submission in submissions:
            submission.refresh_from_db()
            assert submission.status == "SUBMITTED"

    def test_the_card_shows_who_moved_it_and_when(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)

        _withdraw(staff_client, submissions[0].id)

        submissions[0].refresh_from_db()
        assert ("REQUIRES_CORRECTION", "SUBMITTED") in [(entry.get("from_status"), entry.get("to_status")) for entry in submissions[0].status_history]

    def test_the_next_action_offered_is_an_ordinary_review(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # Иначе кнопка вернула бы номер в очередь и оставила организатора без хода.
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)

        response = _withdraw(staff_client, submissions[0].id)

        assert [item["key"] for item in response.data["data"]["capabilities"]] == ["approve", "return_for_correction", "cancel"]


class TestTheApplicantIsTold:
    def test_a_letter_says_there_is_nothing_left_to_fix(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # Участника попросили письменно — он может прямо сейчас это исправлять.
        festival = _Festival()
        application, submissions = _returned_order(festival, applicant_id)
        mail.outbox.clear()

        _withdraw(staff_client, submissions[0].id)

        assert len(mail.outbox) == 1
        letter = mail.outbox[0]
        assert letter.to == [_APPLICANT_EMAIL]
        assert letter.subject == f"Заявка #{str(application.id)[:8].upper()} снова на рассмотрении"
        assert "Исправлять ничего не нужно" in letter.body

    def test_the_cabinet_says_the_same_thing(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        application, submissions = _returned_order(festival, applicant_id)

        _withdraw(staff_client, submissions[0].id)

        entry = NotificationModel.objects.get(recipient_id=applicant_id)
        # Ничего не просят и ничего не должны — ход снова у организатора.
        assert entry.kind == NotificationKind.APPLICATION_SUBMITTED
        assert entry.link == f"/cabinet/applications/{application.id}"

    def test_a_comment_is_optional_but_carried_when_given(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # «Передумали» не требует обоснования, но если организатор его написал —
        # участник должен его увидеть.
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)
        mail.outbox.clear()

        _withdraw(staff_client, submissions[0].id, comment="Видео всё-таки не нужно.")

        assert "Видео всё-таки не нужно." in mail.outbox[0].body

    def test_the_journal_records_that_the_applicant_was_written_to(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id, performances=2)

        _withdraw(staff_client, submissions[0].id)

        for submission in submissions:
            submission.refresh_from_db()
            assert any("отозван" in entry["text"] for entry in submission.participant_messages)


class TestWhatItRefuses:
    def test_nothing_is_sent_when_there_was_nothing_to_take_back(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)
        SubmissionModel.objects.filter(id=submissions[0].id).update(status="APPROVED")
        mail.outbox.clear()

        response = _withdraw(staff_client, submissions[0].id)

        assert response.status_code == 409
        assert mail.outbox == []
        assert NotificationModel.objects.count() == 0

    def test_an_entry_that_cannot_pass_its_own_checks_stays_put(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Вернуть в очередь значит «это снова можно смотреть», и решает это домен.

        Содержимое остаётся редактируемым, пока номер на доработке, так что обратно
        едет не обязательно то же, что уезжало.
        """
        festival = _Festival()
        _, submissions = _returned_order(festival, applicant_id)
        SubmissionModel.objects.filter(id=submissions[0].id).update(participants=[])
        mail.outbox.clear()

        response = _withdraw(staff_client, submissions[0].id)

        assert response.status_code == 422, response.data
        submissions[0].refresh_from_db()
        assert submissions[0].status == "REQUIRES_CORRECTION"
        assert mail.outbox == []
