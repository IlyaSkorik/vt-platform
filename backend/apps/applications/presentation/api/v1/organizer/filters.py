"""Отбор заявок в очереди организатора — один разбор на экран и на выгрузку.

Фильтры живут здесь, а не в представлении очереди, по одной причине: выгрузка
обязана отдавать ровно то, что организатор видит на экране. Организатор отбирает
жанр и фестиваль, нажимает «Скачать» и получает файл — если он соберётся по
другому правилу, человек узнает об этом, уже отправив его в бухгалтерию. Пока
правило одно, разойтись им негде.

Разбор нарочно снисходителен: пустой параметр не фильтрует, регистр не значит
ничего, неизвестное значение ``hasCorrections`` не считается ни «да», ни «нет».
Очередь — рабочий экран, и ссылка с чужим параметром должна показывать заявки, а
не ошибку.
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework.request import Request

__all__ = ["ProcessingFilters"]


def _flag(raw: str) -> bool | None:
    """``True``/``False`` для «true»/«false»; всё остальное — фильтр не задан."""
    text = raw.strip().lower()
    return text == "true" if text in {"true", "false"} else None


@dataclass(frozen=True, slots=True)
class ProcessingFilters:
    """Чем организатор сузил очередь. Пустое поле не сужает ничем."""

    query: str = ""
    queue: str = ""
    competition_id: str = ""
    status: str = ""
    payment: str = ""
    teacher: str = ""
    #: Жанр отбирается по названию, а не по id: у каждого фестиваля своя строка
    #: справочника, и организатор, выбирая «Вокал», имеет в виду вокал везде.
    nomination: str = ""
    organization: str = ""
    from_date: str = ""
    to_date: str = ""
    has_corrections: bool | None = None
    has_missing_files: bool | None = None

    @classmethod
    def from_request(cls, request: Request) -> ProcessingFilters:
        """Фильтры из query-параметров запроса."""
        params = request.query_params
        return cls(
            query=(params.get("q") or "").strip().lower(),
            queue=(params.get("queue") or "").strip().upper(),
            competition_id=(params.get("competitionId") or "").strip(),
            status=(params.get("status") or "").strip().upper(),
            payment=(params.get("payment") or "").strip().upper(),
            teacher=(params.get("teacher") or "").strip().lower(),
            nomination=(params.get("nomination") or "").strip().lower(),
            organization=(params.get("organization") or "").strip().lower(),
            from_date=(params.get("from") or "").strip(),
            to_date=(params.get("to") or "").strip(),
            has_corrections=_flag(params.get("hasCorrections") or ""),
            has_missing_files=_flag(params.get("hasMissingFiles") or ""),
        )

    def matches(
        self,
        *,
        haystack: str,
        queue: str,
        competition_id: str,
        status: str,
        payment: str,
        teachers_text: str,
        nomination: str,
        submitted_on: str,
        has_corrections: bool,
        has_missing_files: bool,
        organization: str,
    ) -> bool:
        """Проходит ли выступление через все заданные фильтры.

        ``haystack`` — строка поиска по заявке (номер, фамилии, фестиваль, жанр),
        собранная вызывающим; ``submitted_on`` — дата подачи в ISO, потому что
        границы периода приходят с формы тем же форматом и сравниваются как текст.
        """
        if self.query and self.query not in haystack:
            return False
        if self.queue and queue != self.queue:
            return False
        if self.competition_id and competition_id != self.competition_id:
            return False
        if self.status and status != self.status:
            return False
        if self.payment and payment != self.payment:
            return False
        if self.teacher and self.teacher not in teachers_text.lower():
            return False
        if self.nomination and nomination.lower() != self.nomination:
            return False
        if self.organization and self.organization not in organization.lower():
            return False
        if self.from_date and submitted_on < self.from_date:
            return False
        if self.to_date and submitted_on > self.to_date:
            return False
        if self.has_corrections is not None and has_corrections != self.has_corrections:
            return False
        return not (self.has_missing_files is not None and has_missing_files != self.has_missing_files)
