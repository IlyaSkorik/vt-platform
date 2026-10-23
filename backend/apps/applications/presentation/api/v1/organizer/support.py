"""Общее для всех экранов и выгрузок обработки заявок.

Очередь на экране, реестр в Excel и архив бумаг отвечают на один набор мелких
вопросов: какие фестивали вообще видны этому организатору, как зовут заявителя,
сколько длится номер, какие квитанции лежат на заказе. Пока ответы жили в модуле
очереди, выгрузкам приходилось импортировать представление — а представлению,
чтобы собрать выгрузку, импортировать их обратно.

Ничего, кроме этих ответов, здесь нет: ни правил домена, ни форматирования под
конкретный файл. Домен остаётся единственным, кто решает, — эти функции только
читают то, что он уже записал.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff
from apps.organization.presentation.scope import callers_organization_id, is_platform_operator

__all__ = [
    "_QUEUE_BY_STATUS",
    "_StaffView",
    "_applicant_label",
    "_duration_seconds",
    "_missing_type_label",
    "_participant_label",
    "_payer_full_name",
    "_queue_for",
    "_receipt_references",
    "_visible_competitions",
]


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff, IsModuleEnabled.of(OrganizationModule.APPLICATIONS))


#: Какой очереди экрана принадлежит выступление в этом статусе. Очередь — это
#: рабочая стопка организатора, а не состояние домена: в одной стопке лежат
#: статусы, по которым делают одно и то же.
_QUEUE_BY_STATUS: Final = {
    "WAITLISTED": "WAITLIST",
    "SUBMITTED": "NEW",
    "UNDER_REVIEW": "NEW",
    "REQUIRES_CORRECTION": "NEW",
    "APPROVED": "READY",
    "WAITING_PAYMENT": "READY",
    "PAID": "READY",
    "ACCEPTED": "READY",
    "SCHEDULED": "RUNNING",
    "COMPLETED": "RUNNING",
    "CANCELLED": "ARCHIVE",
}


def _visible_competitions(request: Request) -> Any:
    """The competitions this caller's organization runs (all of them, for the operator).

    Everything in the organizer workspace hangs off this queryset — the queues, the
    filters, the exports, the archives — so scoping it here scopes the workspace.
    A caller who is staff of no organization sees nothing rather than everything.
    """
    competitions = CompetitionModel.objects.filter(deleted_at__isnull=True)
    if is_platform_operator(request):
        return competitions
    organization_id = callers_organization_id(request)
    if organization_id is None:
        return competitions.none()
    return competitions.filter(organizer_id=organization_id)


def _receipt_references(payment_receipts: Any) -> list[str]:
    """The stored file of every receipt on an order, oldest first, blanks dropped.

    An order carries a list because its fee is regularly settled by more than one
    transfer; everything downstream (the payment badge, the archive, the reminder)
    asks about the whole list rather than a single document.
    """
    return [reference for entry in payment_receipts or [] if (reference := str((entry or {}).get("file_reference") or "").strip())]


def _payer_full_name(row: Any) -> str | None:
    """The order's payer rendered ``Last First Middle``, or ``None`` if unnamed.

    Only festivals that ask for the contract party have anything in these columns, so
    an absent name is the normal case rather than missing data.
    """
    parts = [str(row.get(key) or "").strip() for key in ("payer_last_name", "payer_first_name", "payer_middle_name")]
    named = [part for part in parts if part]
    return " ".join(named) or None


def _participant_label(entry: Any) -> str:
    """One performer as the organizer knows them — a soloist's name or the group's.

    A collective stores only ``display_name``; a soloist stores the name parts and,
    often, a ``display_name`` repeating them. Reading the parts first keeps the
    order ``Last First Middle`` even when the stored caption was typed the other
    way round.
    """
    person = " ".join(part for key in ("last_name", "first_name", "middle_name") if (part := str(entry.get(key) or "").strip()))
    return person or str(entry.get("display_name") or "").strip()


def _applicant_label(participants: Sequence[Any], *fallbacks: str | None) -> str:
    """Who the entry is for, in one line for the queue card.

    The queue used to print ``applicant_id`` — a raw UUID that tells the organizer
    nothing and cannot be matched against a transfer or a phone call. The performers
    are what they recognise, so the card names the first one and counts the rest;
    only an entry with no performers at all falls back to the studio or the payer.
    """
    names = [label for entry in participants or [] if (label := _participant_label(entry))]
    if names:
        return names[0] if len(names) == 1 else f"{names[0]} и ещё {len(names) - 1}"
    for fallback in fallbacks:
        if fallback and fallback.strip():
            return fallback.strip()
    return "—"


def _duration_seconds(value: Any) -> int:
    """Хронометраж номера в секундах; всё, что не число, считается нулём.

    Длительности складывают в итог по жанру, и одна заявка с испорченным значением
    не должна обнулять или взорвать весь подсчёт.
    """
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _missing_type_label(raw: str) -> str:
    labels = {
        "MUSIC": "Музыка",
        "VIDEO": "Видео",
        "DOCUMENT": "Документы",
        "RECEIPT": "Квитанция",
        "OTHER": "Другое",
    }
    key = str(raw or "").upper()
    return labels.get(key, key)


#: Статусы, в которых очередь определяется не статусом, а квитанцией: заявка либо
#: ещё ждёт оплату, либо уже готова к фестивалю. Отменённая, завершённая,
#: назначенная и возвращённая на исправление к оплате отношения не имеют.
_PAYMENT_DRIVEN_QUEUE: Final = frozenset({"REQUIRES_CORRECTION", "SCHEDULED", "COMPLETED", "CANCELLED"})


def _queue_for(status: str, *, has_receipts: bool) -> str:
    """В какой стопке организатора лежит выступление.

    Статуса мало: одобренная заявка стоит либо в «ожидают оплату», либо в «готовы
    к фестивалю», и отличает их приложенная квитанция, а не состояние домена.
    Оплату организатор проводит задним числом, и стопка должна меняться в тот
    момент, когда появилась бумага, а не когда до неё дошли руки.
    """
    queue = _QUEUE_BY_STATUS.get(status, "ARCHIVE")
    if status in _PAYMENT_DRIVEN_QUEUE:
        return queue
    return "READY" if has_receipts else "WAITING_PAYMENT"
