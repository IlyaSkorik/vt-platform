"""Какие заявки сейчас отобраны — один ответ на все выгрузки организатора.

Очередь на экране, таблица реестра и архив бумаг отвечают на один и тот же
вопрос: какие выступления организатор сейчас разбирает. Отбор поэтому живёт
здесь, а не в каждом из них по разу. Организатор ставит фильтр «назначены на
фестиваль», жмёт «Скачать документы» и ждёт квитанции по этим заявкам, а не по
всему сезону, — и если бы архив собирался по собственному правилу, узнал бы об
этом, уже отправив папку в бухгалтерию.

Читается всё пакетом: заказы, справочники фестиваля и учреждения участников —
по одному запросу на выгрузку, а не по запросу на строку. Реестр на тысячу
выступлений — обычный размер сезона.

Границы организации проверяются здесь же (``_visible_competitions``): выгрузка —
это место, где недостающий скоуп отдаёт чужие бумаги целой папкой.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from rest_framework.request import Request

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel

from .filters import ProcessingFilters
from .support import (
    _QUEUE_BY_STATUS,
    _applicant_label,
    _payer_full_name,
    _queue_for,
    _receipt_references,
    _visible_competitions,
)

__all__ = ["OrderFacts", "SelectedSubmission", "Selection", "Taxonomy", "select_submissions"]


def _money(raw: Any) -> float | None:
    """Сумма числом, чтобы Excel её складывал; мусор — пусто, а не ноль."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _teacher_names(entries: Iterable[Mapping[str, Any]]) -> str:
    """Педагоги с ролями: «Иванова Мария (руководитель)»."""
    rendered: list[str] = []
    for entry in entries:
        name = " ".join(part for key in ("last_name", "first_name", "middle_name") if (part := str(entry.get(key) or "").strip()))
        if not name:
            continue
        role = str(entry.get("role") or "").strip()
        rendered.append(f"{name} ({role})" if role else name)
    return "; ".join(rendered)


@dataclass(frozen=True, slots=True)
class Taxonomy:
    """Справочники фестивалей выгрузки: ``id -> название``, по одному запросу на вид."""

    nominations: Mapping[str, str]
    disciplines: Mapping[str, str]
    age_categories: Mapping[str, str]
    participant_groups: Mapping[str, str]
    participation_formats: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class OrderFacts:
    """Заказ так, как его читают выгрузки: деньги, бумаги и кто за него платит."""

    id: str
    status: str
    organization_name: str
    payer_name: str | None
    #: Файлы квитанций в порядке загрузки. Заказ регулярно гасят несколькими
    #: переводами, и каждый приносит свой слип.
    receipts: tuple[str, ...]
    total_amount: float | None
    currency: str
    paid_at: datetime | None
    submission_ids: tuple[str, ...]
    #: Кто в заказе выступает первым — им подписывают папку с его бумагами. Снимок
    #: с самой заявки: имени в ней может и не быть, и тогда папку назовут номером.
    lead_performer: str
    #: Несёт ли хоть один номер заказа справку о льготе. Скидка считается по
    #: заказу целиком, поэтому вопрос осмыслен именно на этом уровне.
    has_benefit: bool


@dataclass(frozen=True, slots=True)
class SelectedSubmission:
    """Одно отобранное выступление и всё, что о нём знают обе выгрузки."""

    model: SubmissionModel
    order: OrderFacts | None
    queue: str
    #: ``RECEIPT_ATTACHED`` / ``RECEIPT_MISSING`` — тот же словарь, что у фильтра оплаты.
    payment: str
    applicant: str
    organization: str
    teachers_text: str
    nomination: str
    has_missing_files: bool
    has_benefit: bool

    @property
    def id(self) -> str:
        return str(self.model.id)

    @property
    def order_id(self) -> str:
        return self.order.id if self.order is not None else ""

    @property
    def number(self) -> str:
        """Номер заявки — то же, что организатор видит на карточке и ищет в поиске."""
        return (self.order_id or self.id)[:8].upper()


@dataclass(frozen=True, slots=True)
class Selection:
    """Что попало в отбор, и чем подписать идентификаторы в нём."""

    filters: ProcessingFilters
    #: ``id -> название`` фестивалей, видимых этому организатору.
    competitions: Mapping[str, str]
    taxonomy: Taxonomy
    entries: tuple[SelectedSubmission, ...]

    @property
    def orders(self) -> tuple[OrderFacts, ...]:
        """Заказы отобранных выступлений, каждый по разу, в порядке отбора."""
        seen: dict[str, OrderFacts] = {}
        for entry in self.entries:
            if entry.order is not None:
                seen.setdefault(entry.order.id, entry.order)
        return tuple(seen.values())

    @property
    def competition_title(self) -> str | None:
        """Название фестиваля, если отобран ровно один; иначе ``None``."""
        return self.competitions.get(self.filters.competition_id)


def _taxonomy_names(model: Any, competition_ids: Sequence[uuid.UUID]) -> dict[str, str]:
    return {
        str(row["id"]): str(row["name"])
        for row in model.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
    }


def _organizations(submissions: Sequence[SubmissionModel]) -> dict[str, str]:
    """Учреждения выступающих по выступлениям — одним запросом в реестр.

    Правило то же, что на карточке (``_educational_organizations``): учреждение,
    которое организатор пригвоздил прямо в заявке, отменяет поход в реестр, а
    реестровые идут в порядке «основное первым». Разница только в том, что здесь
    спрашивается сразу обо всех участниках выгрузки.
    """
    registry_ids: set[uuid.UUID] = set()
    for model in submissions:
        for participant in model.participants or []:
            if str(participant.get("organization_name") or "").strip():
                continue
            raw = str(participant.get("registry_participant_id") or "").strip()
            if not raw:
                continue
            try:
                registry_ids.add(uuid.UUID(raw))
            except (ValueError, TypeError):
                continue

    by_participant: dict[str, list[str]] = defaultdict(list)
    if registry_ids:
        rows = (
            ParticipantOrganizationMembershipModel.objects.filter(
                participant_id__in=registry_ids,
                deleted_at__isnull=True,
                organization__deleted_at__isnull=True,
            )
            .order_by("-is_primary", "organization__name")
            .values_list("participant_id", "organization__name")
        )
        for participant_id, name in rows:
            if cleaned := str(name or "").strip():
                by_participant[str(participant_id)].append(cleaned)

    result: dict[str, str] = {}
    for model in submissions:
        # dict, а не set: два участника из одной школы не должны печатать её дважды,
        # а порядок «основное первым» обязан пережить дедупликацию.
        seen: dict[str, None] = {}
        for participant in model.participants or []:
            if pinned := str(participant.get("organization_name") or "").strip():
                seen.setdefault(pinned, None)
                continue
            for name in by_participant.get(str(participant.get("registry_participant_id") or ""), []):
                seen.setdefault(name, None)
        result[str(model.id)] = ", ".join(seen)
    return result


def _carries_benefit(model: SubmissionModel) -> bool:
    """Приложена ли к номеру справка о льготе.

    ``BENEFIT``, а не ``DOCUMENT``: обязательная бумага, которую фестиваль просит у
    всех, — не заявка на скидку, и считать её льготой значило бы записать в
    льготники весь фестиваль.
    """
    return any(str((entry or {}).get("type") or "") == "BENEFIT" for entry in model.attachments or [])


def select_submissions(request: Request) -> Selection:
    """Выступления, прошедшие текущий отбор, в границах организации вызывающего."""
    filters = ProcessingFilters.from_request(request)
    competitions = list(_visible_competitions(request).values("id", "title").order_by("title"))
    competition_ids = [row["id"] for row in competitions]
    competition_name = {str(row["id"]): str(row["title"]) for row in competitions}
    taxonomy = Taxonomy(
        nominations=_taxonomy_names(CategoryModel, competition_ids),
        disciplines=_taxonomy_names(DisciplineModel, competition_ids),
        age_categories=_taxonomy_names(AgeCategoryModel, competition_ids),
        participant_groups=_taxonomy_names(ParticipantGroupModel, competition_ids),
        participation_formats=_taxonomy_names(ParticipationFormatModel, competition_ids),
    )

    submissions = list(
        SubmissionModel.objects.filter(
            deleted_at__isnull=True,
            competition_id__in=competition_ids,
            status__in=list(_QUEUE_BY_STATUS),
        ).order_by("-updated_at")
    )
    organizations = _organizations(submissions)
    benefit_submissions = {str(model.id) for model in submissions if _carries_benefit(model)}

    order_rows = list(
        ApplicationModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values(
            "id",
            "status",
            "organization_name",
            "payer_last_name",
            "payer_first_name",
            "payer_middle_name",
            "submission_refs",
            "payment_receipts",
            "total_price",
            "paid_at",
        )
    )
    orders: dict[str, OrderFacts] = {}
    order_by_submission: dict[str, str] = {}
    for row in order_rows:
        order_id = str(row["id"])
        total_price = row.get("total_price") or {}
        refs = row.get("submission_refs") or []
        submission_ids = tuple(str(ref.get("submission_id") or "") for ref in refs if str(ref.get("submission_id") or ""))
        orders[order_id] = OrderFacts(
            id=order_id,
            status=str(row.get("status") or ""),
            organization_name=str(row.get("organization_name") or ""),
            payer_name=_payer_full_name(row),
            receipts=tuple(_receipt_references(row.get("payment_receipts"))),
            # Итог лежит под ключом "total" (см. ApplicationMapper); "amount" — ключ
            # одиночной Money, принимается, чтобы прочиталась старая строка.
            total_amount=_money(total_price.get("total") or total_price.get("amount")),
            currency=str(total_price.get("currency") or "").strip(),
            paid_at=row.get("paid_at"),
            submission_ids=submission_ids,
            lead_performer=next((name for ref in refs if (name := str(ref.get("participant_display_name") or "").strip())), ""),
            has_benefit=any(submission_id in benefit_submissions for submission_id in submission_ids),
        )
        for submission_id in submission_ids:
            order_by_submission[submission_id] = order_id

    entries: list[SelectedSubmission] = []
    for model in submissions:
        submission_id = str(model.id)
        performance = model.performance or {}
        participants = model.participants or []
        order = orders.get(order_by_submission.get(submission_id, ""))

        receipts = order.receipts if order is not None else ()
        payment = "RECEIPT_ATTACHED" if receipts else "RECEIPT_MISSING"
        queue = _queue_for(model.status, has_receipts=bool(receipts))

        nomination = taxonomy.nominations.get(str(performance.get("nomination_id") or ""), "")
        order_organization = order.organization_name if order is not None else ""
        organization = organizations.get(submission_id) or order_organization
        teachers_text = _teacher_names(model.teachers or [])
        applicant = _applicant_label(participants, order_organization, order.payer_name if order is not None else None)
        order_id = order.id if order is not None else ""

        if not filters.matches(
            haystack=" ".join(
                [
                    submission_id,
                    order_id,
                    (order_id or submission_id)[:8].upper(),
                    str(performance.get("title") or ""),
                    applicant,
                    str(model.applicant_id),
                    nomination,
                    competition_name.get(str(model.competition_id), ""),
                    organization,
                    teachers_text,
                ]
            ).lower(),
            queue=queue,
            competition_id=str(model.competition_id),
            status=model.status,
            payment=payment,
            teachers_text=teachers_text,
            nomination=nomination,
            submitted_on=model.created_at.date().isoformat(),
            has_corrections=model.status == "REQUIRES_CORRECTION",
            has_missing_files=any(not (entry or {}).get("resolved_at") for entry in model.missing_files_requests or []),
            organization=organization,
        ):
            continue

        entries.append(
            SelectedSubmission(
                model=model,
                order=order,
                queue=queue,
                payment=payment,
                applicant=applicant,
                organization=organization,
                teachers_text=teachers_text,
                nomination=nomination,
                has_missing_files=any(not (entry or {}).get("resolved_at") for entry in model.missing_files_requests or []),
                has_benefit=submission_id in benefit_submissions,
            )
        )

    return Selection(filters=filters, competitions=competition_name, taxonomy=taxonomy, entries=tuple(entries))
