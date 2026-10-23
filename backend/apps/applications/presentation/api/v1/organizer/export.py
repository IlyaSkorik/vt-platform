"""Реестр заявок как таблица: всё, что знает карточка, в одном файле.

Организатор живёт в двух местах. Очередь на экране — чтобы разобрать заявку:
одна открыта, остальные ждут. Таблица — чтобы работать со всеми сразу: обзвонить
тех, кто не оплатил, свести льготников, отдать список в бухгалтерию, посчитать
минуты по жанру. Экран для второго не годится, и до сих пор вместо таблицы
выгружался столбец UUID — файл, который нельзя ни прочитать, ни переслать.

**Строка — это выступление, а не заказ.** Заявка на двух детей с тремя номерами
— это три строки, и это то, что организатор пересчитывает: программа, жанры и
хронометраж живут по номерам. Деньги живут по заказу, поэтому сумма заказа
повторяется в каждой его строке (рядом стоит «Номеров в заказе», чтобы повтор был
виден) — складывать безопасно колонку «Стоимость номера».

**Оплата и льгота — отдельными колонками «Да»/«Нет».** Это первые два вопроса к
любой заявке, и ответ на них не выводится из статуса: заказ бывает «Ожидает
оплаты» с уже приложенной квитанцией, которую никто не успел провести, и бывает
со справкой о льготе, объясняющей, почему сумма меньше прайса. Текстовое «Да»
вместо галочки — чтобы в Excel работал обычный фильтр по столбцу.

Выгружается ровно то, что отобрано на экране (:mod:`.selection`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import IO, Any, Final
from zoneinfo import ZoneInfo

from rest_framework.request import Request

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.teachers.infrastructure.models import TeacherModel
from shared.spreadsheet import Cell, SheetColumn, write_workbook

from .selection import Selection, select_submissions
from .support import _duration_seconds, _missing_type_label, _participant_label

__all__ = ["applications_workbook"]

#: Организатор читает время по Минску, а хранится оно в UTC.
_DISPLAY_TZ: Final = ZoneInfo("Europe/Minsk")

#: Статусы выступления по-русски. То же, что на карточке, — файл и экран не должны
#: называть одно состояние двумя словами.
_STATUS_LABELS: Final = {
    "DRAFT": "Черновик",
    "WAITLISTED": "Лист ожидания",
    "SUBMITTED": "Подана",
    "UNDER_REVIEW": "На рассмотрении",
    "REQUIRES_CORRECTION": "На исправлении",
    "APPROVED": "Одобрена",
    "WAITING_PAYMENT": "Ожидает оплаты",
    "PAID": "Оплачена",
    "ACCEPTED": "Подтверждена",
    "SCHEDULED": "В расписании",
    "COMPLETED": "Завершена",
    "CANCELLED": "Отменена",
}

#: Статусы заказа по-русски.
_ORDER_STATUS_LABELS: Final = {
    "DRAFT": "Черновик",
    "SUBMITTED": "Подан",
    "WAITING_PAYMENT": "Ожидает оплаты",
    "PAID": "Оплачен",
    "COMPLETED": "Завершён",
    "CANCELLED": "Отменён",
}

#: Очереди по-русски — теми же словами, что подписаны вкладки на экране.
_QUEUE_LABELS: Final = {
    "WAITLIST": "Лист ожидания",
    "NEW": "На доработке",
    "WAITING_PAYMENT": "Ожидают оплату",
    "READY": "Готовы к фестивалю",
    "RUNNING": "Назначены на фестиваль",
    "ARCHIVE": "Отменены",
}

#: Колонки реестра по порядку: сперва чем заявка опознаётся, потом кто и что
#: выступает, потом деньги и бумаги, и в самом конце идентификаторы — они нужны
#: поддержке, а не тому, кто таблицу читает.
_COLUMNS: Final = (
    SheetColumn(heading="№ заявки", width=12),
    SheetColumn(heading="Фестиваль"),
    SheetColumn(heading="Статус", width=18),
    SheetColumn(heading="Очередь", width=22),
    SheetColumn(heading="Заявитель"),
    SheetColumn(heading="Выступающие", width=40),
    SheetColumn(heading="Человек в номере", width=18),
    SheetColumn(heading="Даты рождения", width=24),
    SheetColumn(heading="Учреждение", width=30),
    SheetColumn(heading="Номер"),
    SheetColumn(heading="Жанр", width=20),
    SheetColumn(heading="Дисциплина", width=20),
    SheetColumn(heading="Возрастная категория", width=22),
    SheetColumn(heading="Состав", width=18),
    SheetColumn(heading="Форма участия", width=20),
    SheetColumn(heading="Хронометраж", width=14),
    SheetColumn(heading="Возрастной состав", width=26),
    SheetColumn(heading="Комментарий участника", width=40),
    SheetColumn(heading="Педагоги", width=36),
    SheetColumn(heading="Телефоны педагогов", width=24),
    SheetColumn(heading="Стоимость номера", width=18),
    SheetColumn(heading="Сумма заказа", width=16),
    SheetColumn(heading="Номеров в заказе", width=18),
    SheetColumn(heading="Валюта", width=10),
    SheetColumn(heading="Плательщик", width=30),
    SheetColumn(heading="Оплата", width=12),
    SheetColumn(heading="Квитанций", width=12),
    SheetColumn(heading="Оплачено", width=18),
    SheetColumn(heading="Статус заказа", width=18),
    SheetColumn(heading="Льгота", width=10),
    SheetColumn(heading="Документов на льготу", width=22),
    SheetColumn(heading="Льгота в заказе", width=16),
    SheetColumn(heading="Фонограмма", width=14),
    SheetColumn(heading="Видео/фото", width=14),
    SheetColumn(heading="Прочие документы", width=20),
    SheetColumn(heading="Запрошены файлы", width=26),
    SheetColumn(heading="Подана", width=18),
    SheetColumn(heading="Изменена", width=18),
    SheetColumn(heading="ID выступления", width=38),
    SheetColumn(heading="ID заказа", width=38),
)


def _yes_no(value: bool) -> str:
    """«Да»/«Нет» вместо галочки: по словам в Excel фильтруют, по пустоте — нет."""
    return "Да" if value else "Нет"


def _moment(value: Any) -> str:
    """Дата и время по Минску как ``ГГГГ-ММ-ДД ЧЧ:ММ``.

    Не «01.03.2026»: столбец в таком виде сортируется как текст — по дню, потом по
    месяцу, — и реестр, отсортированный по дате подачи, перемешивает сезоны.
    """
    if value is None:
        return ""
    moment = value.astimezone(_DISPLAY_TZ) if getattr(value, "tzinfo", None) is not None else value
    return f"{moment:%Y-%m-%d %H:%M}"


def _duration_label(seconds: int) -> str:
    """Хронометраж как ``М:СС``; ноль — пусто, а не «0:00»."""
    return f"{seconds // 60}:{seconds % 60:02d}" if seconds > 0 else ""


def _amount(raw: Any) -> float | None:
    """Сумма числом, чтобы Excel её складывал; мусор — пусто, а не ноль."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _performers(entries: Iterable[Mapping[str, Any]]) -> str:
    """Все выступающие одного номера в одну ячейку."""
    return "; ".join(label for entry in entries if (label := _participant_label(entry)))


def _teacher_phones(submissions: Iterable[SubmissionModel]) -> dict[str, str]:
    """Телефоны педагогов всей выгрузки — одним запросом в справочник кабинета.

    Телефон лежит в справочнике, а не на заявке, и ради реестра на сотню строк
    незачем ходить туда по разу на строку. Педагог, вписанный руками, остаётся без
    телефона: звонить некуда, и пустая ячейка честнее выдуманной.
    """
    directory_ids = {
        directory_id
        for model in submissions
        for teacher in model.teachers or []
        if (directory_id := str(teacher.get("directory_teacher_id") or "").strip())
    }
    if not directory_ids:
        return {}
    rows = TeacherModel.objects.filter(pk__in=directory_ids, deleted_at__isnull=True).values_list("id", "phone")
    return {str(directory_id): cleaned for directory_id, phone in rows if (cleaned := (phone or "").strip())}


def _attachment_counts(attachments: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Сколько файлов каждого вида приложено к выступлению."""
    counts: dict[str, int] = defaultdict(int)
    for entry in attachments:
        counts[str((entry or {}).get("type") or "").upper()] += 1
    return counts


def _requested_files(requests: Iterable[Mapping[str, Any]]) -> str:
    """Какие файлы у участника ещё ждут — только незакрытые запросы."""
    pending = {
        _missing_type_label(str(kind)) for entry in requests if not (entry or {}).get("resolved_at") for kind in (entry or {}).get("types") or []
    }
    return ", ".join(sorted(pending))


def _row(entry: Any, *, selection: Selection, phones: Mapping[str, str]) -> tuple[Cell, ...]:
    """Одно выступление как строка реестра."""
    model = entry.model
    performance = model.performance or {}
    participants = model.participants or []
    teachers = model.teachers or []
    order = entry.order
    attachments = _attachment_counts(model.attachments or [])
    price = model.price_snapshot or {}
    taxonomy = selection.taxonomy
    return (
        entry.number,
        selection.competitions.get(str(model.competition_id), ""),
        _STATUS_LABELS.get(model.status, model.status),
        _QUEUE_LABELS.get(entry.queue, entry.queue),
        entry.applicant,
        _performers(participants),
        sum(int(item.get("member_count", 1) or 1) for item in participants),
        "; ".join(str(item.get("birth_date") or "") for item in participants if item.get("birth_date")),
        entry.organization,
        str(performance.get("title") or ""),
        entry.nomination,
        taxonomy.disciplines.get(str(performance.get("discipline_id") or ""), ""),
        taxonomy.age_categories.get(str(performance.get("age_category_id") or ""), ""),
        taxonomy.participant_groups.get(str(performance.get("participant_group_id") or ""), ""),
        taxonomy.participation_formats.get(str(performance.get("participation_format_id") or ""), ""),
        _duration_label(_duration_seconds(performance.get("duration_seconds"))),
        str(performance.get("age_composition") or ""),
        str(performance.get("comment") or ""),
        entry.teachers_text,
        "; ".join(phone for teacher in teachers if (phone := phones.get(str(teacher.get("directory_teacher_id") or ""), ""))),
        _amount(price.get("amount")),
        order.total_amount if order is not None else None,
        len(order.submission_ids) if order is not None and order.submission_ids else 1,
        str(price.get("currency") or "") or (order.currency if order is not None else ""),
        (order.payer_name or "") if order is not None else "",
        _yes_no(entry.payment == "RECEIPT_ATTACHED"),
        len(order.receipts) if order is not None else 0,
        _moment(order.paid_at if order is not None else None),
        _ORDER_STATUS_LABELS.get(order.status, order.status) if order is not None else "",
        _yes_no(entry.has_benefit),
        attachments.get("BENEFIT", 0),
        _yes_no(order.has_benefit if order is not None else entry.has_benefit),
        _yes_no(attachments.get("MUSIC", 0) > 0),
        _yes_no(attachments.get("VIDEO", 0) + attachments.get("IMAGE", 0) > 0),
        _yes_no(attachments.get("DOCUMENT", 0) > 0),
        _requested_files(model.missing_files_requests or []),
        _moment(model.created_at),
        _moment(model.updated_at),
        entry.id,
        entry.order_id,
    )


def applications_workbook(request: Request) -> tuple[IO[bytes], str]:
    """Реестр отобранных заявок и имя файла, под которым его сохранят."""
    selection = select_submissions(request)
    phones = _teacher_phones(entry.model for entry in selection.entries)
    rows = [_row(entry, selection=selection, phones=phones) for entry in selection.entries]
    workbook = write_workbook(columns=_COLUMNS, rows=rows, sheet_title="Заявки")
    return workbook, _filename(selection.competition_title)


def _filename(competition_title: str | None) -> str:
    """Имя файла: с названием фестиваля, когда выгружен один из них.

    Организатор ведёт несколько фестивалей и складывает выгрузки в одну папку —
    три файла «Заявки.xlsx» там неразличимы.
    """
    title = (competition_title or "").strip()
    return f"Заявки — {title}.xlsx" if title else "Заявки.xlsx"
