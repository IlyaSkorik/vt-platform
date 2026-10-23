"""Реестр заявок в Excel: что организатор отдаёт бухгалтерии и обзванивает по списку.

Проверяется не «файл скачался», а три вещи, ради которых реестр и делали: в нём
есть поля, а не одни идентификаторы; оплата и льгота отвечают «Да»/«Нет» сами по
себе, не заставляя выводить ответ из статуса; и выгружается ровно то, что
отобрано на экране — в границах своей организации.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from openpyxl import load_workbook
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.domain.entities import Application
from apps.applications.domain.value_objects import ApplicationId, CompetitionId, FileReference, UserId
from apps.applications.infrastructure.mappers.application_mapper import ApplicationMapper
from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_EXPORT = "/api/v1/staff/applications/export"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _authenticated(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    access = _authenticated(client, "organizer@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


def _festival(title: str = "Фестиваль") -> uuid.UUID:
    """Фестиваль своей организации — реестр за её границы не выходит."""
    organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
    assert organization_id is not None, "expected a provisioned organization"
    competition = CompetitionModel.objects.create(organizer_id=organization_id, status="PUBLISHED", title=title, season="2025/2026")
    return competition.id


def _foreign_festival() -> uuid.UUID:
    """Фестиваль чужой организации."""
    other = OrganizationModel.objects.create(name="Другой организатор", slug=f"other-{uuid.uuid4().hex[:8]}")
    competition = CompetitionModel.objects.create(organizer_id=other.id, status="PUBLISHED", title="Чужой", season="2025/2026")
    return competition.id


def _receipts_json(references: tuple[str, ...]) -> list[dict[str, Any]]:
    """Квитанции ровно в том виде, в каком их пишет агрегат.

    Через настоящий агрегат и маппер, а не руками: квитанция лежит под
    ``file_reference``, а вложение заявки — под ``file``, и фикстура, угадавшая
    однажды, уже делала сломанный архив похожим на проверенный.
    """
    application, _ = Application.create(
        application_id=ApplicationId.generate(),
        competition_id=CompetitionId.from_uuid(uuid7()),
        applicant_id=UserId.from_uuid(uuid7()),
        now=NOW,
    )
    for reference in references:
        application.upload_payment_receipt(file=FileReference(reference), now=NOW)
    receipts: list[dict[str, Any]] = ApplicationMapper.to_model(application).payment_receipts
    return receipts


def _entry(
    *,
    competition_id: uuid.UUID,
    performer: str = "Иванова Анна",
    status: str = "SUBMITTED",
    nomination_id: uuid.UUID | None = None,
    receipts: tuple[str, ...] = (),
    benefit: bool = False,
    music: bool = False,
    price: str | None = None,
    teacher: str | None = None,
) -> tuple[SubmissionModel, ApplicationModel]:
    """Одно выступление со своим заказом — минимум, который печатает строку."""
    attachments: list[dict[str, Any]] = []
    if benefit:
        attachments.append({"id": str(uuid.uuid4()), "type": "BENEFIT", "file": "uploads/benefit.pdf", "caption": "Справка"})
    if music:
        attachments.append({"id": str(uuid.uuid4()), "type": "MUSIC", "file": "uploads/track.mp3", "caption": None})
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        performance={
            "title": "Калинка",
            "duration_seconds": 185,
            "nomination_id": str(nomination_id) if nomination_id else str(uuid.uuid4()),
            "discipline_id": str(uuid.uuid4()),
            "age_category_id": str(uuid.uuid4()),
            "participant_group_id": str(uuid.uuid4()),
            "participation_format_id": str(uuid.uuid4()),
            "comment": "",
            "age_composition": "",
        },
        participants=[{"id": str(uuid.uuid4()), "last_name": performer.split()[0], "first_name": performer.split()[1], "member_count": 1}],
        teachers=[{"id": str(uuid.uuid4()), "last_name": teacher, "first_name": "Мария", "middle_name": None, "role": "руководитель"}]
        if teacher
        else [],
        attachments=attachments,
        price_snapshot={"amount": price, "currency": "BYN", "calculated_at": NOW.isoformat()} if price else None,
    )
    application = ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=submission.applicant_id,
        status="WAITING_PAYMENT",
        submission_refs=[{"submission_id": str(submission.id), "participant_display_name": performer}],
        payment_receipts=_receipts_json(receipts),
        total_price={"total": price, "submissions_total": price, "services_total": "0", "currency": "BYN", "calculated_at": NOW.isoformat()}
        if price
        else None,
    )
    return submission, application


def _sheet(response: Any) -> list[dict[str, Any]]:
    """Книгу — в список строк, подписанных заголовками колонок."""
    workbook = load_workbook(io.BytesIO(b"".join(response)))
    sheet = workbook["Заявки"]
    rows = list(sheet.values)
    headings = [str(cell) for cell in rows[0]]
    return [dict(zip(headings, row, strict=False)) for row in rows[1:]]


class TestApplicationsExport:
    def test_the_file_is_a_workbook_with_named_columns(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _entry(competition_id=competition_id)

        response = staff_client.get(f"{_EXPORT}?competitionId={competition_id}")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        # Имя с названием фестиваля: выгрузки трёх фестивалей ложатся в одну папку.
        assert "%D0%97%D0%B0%D1%8F%D0%B2%D0%BA%D0%B8" in response["Content-Disposition"]
        row = _sheet(response)[0]
        assert row["Фестиваль"] == "Фестиваль"
        assert row["Выступающие"] == "Иванова Анна"
        assert row["Номер"] == "Калинка"
        assert row["Хронометраж"] == "3:05"

    def test_payment_and_benefit_answer_for_themselves(self, staff_client: APIClient) -> None:
        # Два вопроса, с которых начинается разбор заявки. Ни на один из них статус
        # не отвечает: заказ «ожидает оплаты» с приложенной квитанцией — обычное дело.
        competition_id = _festival()
        _entry(competition_id=competition_id, performer="Иванова Анна", receipts=("uploads/receipt.pdf",), benefit=True)
        _entry(competition_id=competition_id, performer="Петров Пётр")

        rows = {row["Выступающие"]: row for row in _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}"))}

        assert rows["Иванова Анна"]["Оплата"] == "Да"
        assert rows["Иванова Анна"]["Квитанций"] == 1
        assert rows["Иванова Анна"]["Льгота"] == "Да"
        assert rows["Иванова Анна"]["Документов на льготу"] == 1
        assert rows["Петров Пётр"]["Оплата"] == "Нет"
        assert rows["Петров Пётр"]["Льгота"] == "Нет"

    def test_money_is_a_number_so_the_column_adds_up(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _entry(competition_id=competition_id, price="45.50")

        row = _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}"))[0]

        assert row["Стоимость номера"] == 45.5
        assert row["Сумма заказа"] == 45.5
        assert row["Валюта"] == "BYN"

    def test_files_are_listed_by_kind(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _entry(competition_id=competition_id, music=True)

        row = _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}"))[0]

        assert row["Фонограмма"] == "Да"
        assert row["Видео/фото"] == "Нет"

    def test_the_genre_is_printed_by_name(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        nomination = CategoryModel.objects.create(competition_id=competition_id, name="Вокал")
        _entry(competition_id=competition_id, nomination_id=nomination.id)

        row = _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}"))[0]

        assert row["Жанр"] == "Вокал"

    def test_the_teacher_travels_with_their_role(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _entry(competition_id=competition_id, teacher="Сидорова")

        row = _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}"))[0]

        assert row["Педагоги"] == "Сидорова Мария (руководитель)"

    def test_only_what_the_screen_selected_is_exported(self, staff_client: APIClient) -> None:
        # Отбор на экране и содержимое файла — одно и то же правило, иначе организатор
        # узнает о расхождении, уже отправив выгрузку дальше.
        competition_id = _festival()
        _entry(competition_id=competition_id, performer="Иванова Анна", status="SCHEDULED")
        _entry(competition_id=competition_id, performer="Петров Пётр", status="SUBMITTED")

        rows = _sheet(staff_client.get(f"{_EXPORT}?competitionId={competition_id}&status=SCHEDULED"))

        assert [row["Выступающие"] for row in rows] == ["Иванова Анна"]

    def test_another_organizations_festival_never_appears(self, staff_client: APIClient) -> None:
        # Выгрузка — это место, где недостающий скоуп отдаёт чужие заявки целым файлом.
        _festival()
        _entry(competition_id=_foreign_festival(), performer="Сидоров Иван")

        rows = _sheet(staff_client.get(_EXPORT))

        assert rows == []
