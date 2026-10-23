"""Перевыпуск дипломов, данные которых разошлись с заявкой.

Диплом хранит замороженный снимок, и это правильно: документ, выданный на руки,
не должен меняться оттого, что кто-то поправил заявку. Но у заморозки есть
обратная сторона, которую фестиваль уже встретил. Организатор исправлял
учреждение за участника **после** того, как дипломы были сгенерированы, — и
исправление никуда не попало: ни в PDF, ни в кабинет, ни на страницу проверки по
QR. Даже повторная публикация результатов его не подхватывает: награждение
перерисовывает PDF из уже сохранённого снимка, а пересобирает снимок только для
диплома, которого ещё нет.

Эта служба — единственный путь, которым снимок пересобирается у существующего
диплома, и устроена она вокруг одного правила:

**Чего не изменилось, того не касаемся.** Снимок сверяется с пересобранным, и
совпадение означает выход: ни записи, ни рендера, ни нового ``version``. Иначе
«перевыпуск после правки одного учреждения» переписал бы весь реестр фестиваля,
и в журнале документов не осталось бы следа, по которому видно, какие из них
действительно менялись.

**Документ остаётся тем же документом.** Идентификатор, номер в реестре и токен
проверки не трогаются — напечатанный QR продолжает вести на этот самый диплом, а
обновлённая страница проверки покажет уже исправленные данные. Степень и имя
участника коллектива переносятся из прежнего снимка (:meth:`Diploma._merged`).
Ключ файла в хранилище детерминирован (номер + фестиваль), поэтому ссылка,
которая уже есть у участника, после перерисовки ведёт на обновлённый PDF.

**Перерисовывается только копия участника.** Печатный экземпляр — это бланк «до
церемонии», он давно распечатан, и переписывать его файл незачем; к тому же он
рисуется без степени, а снимок к этому моменту её уже несёт — перерисовка
добавила бы в печатный пакет то, чего в нём быть не должно. Диплом, который ещё
не выпущен участнику, PDF не получает вовсе: он появится при публикации
результатов, уже из исправленного снимка.

**Сбой одного диплома не трогает остальные.** Удалённая заявка, отсутствующий
шаблон, неудавшийся рендер — каждый случай отдаётся в отчёт как пропуск с
причиной, а сам диплом остаётся нетронутым целиком: снимок без перерисованного
PDF означал бы кабинет, который показывает одно, и файл, в котором написано
другое.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final

from apps.diplomas.application.interfaces import (
    DiplomaRepository,
    DiplomaSnapshotSource,
    PrintPackageWorkspace,
)
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = ["DiplomaSnapshotRefreshService", "FieldChange", "RefreshOutcome", "RefreshStatus"]


class RefreshStatus(Enum):
    """Что стало с одним дипломом.

    ``UNCHANGED`` — снимок совпал с пересобранным; диплом не тронут.
    ``PLANNED``   — расхождение найдено, но это разведка (``apply=False``).
    ``UPDATED``   — снимок пересобран и, если копия участника была, перерисована.
    ``SKIPPED``   — расхождение есть, но перевыпустить нельзя; причина в отчёте.
    """

    UNCHANGED = "UNCHANGED"
    PLANNED = "PLANNED"
    UPDATED = "UPDATED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class FieldChange:
    """Одно поле снимка, которое разошлось: как подписать, что было, что стало."""

    field: str
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class RefreshOutcome:
    """Что произошло с одним дипломом и почему."""

    diploma_id: uuid.UUID
    number: str
    status: RefreshStatus
    recipient: str = ""
    changes: tuple[FieldChange, ...] = ()
    #: Заполнена только у ``SKIPPED`` — человекочитаемая причина для отчёта.
    reason: str | None = None
    #: Была ли при этом заново отрисована копия участника. У диплома, который ещё
    #: не выпущен, снимок обновляется, а PDF не появляется — и это не пропуск.
    rerendered: bool = False


#: Подписи полей снимка для отчёта — ими же названы колонки, которые организатор
#: сверяет глазами, прежде чем разрешить запись.
_LABELS: Final = {
    "participant": "Участник",
    "organization": "Учреждение",
    "teachers": "Педагоги",
    "nomination": "Номинация",
    "performance": "Номер",
    "competition": "Фестиваль",
}


def _render(value: object) -> str:
    """Значение поля снимка одной строкой, пустое — как «—»."""
    if value is None:
        return "—"
    if isinstance(value, tuple):
        return "; ".join(_render(item) for item in value) or "—"
    parts = [
        f"{key}={rendered}"
        for key, raw in sorted(vars(value).items() if not hasattr(value, "to_dict") else value.to_dict().items())
        if (rendered := ("" if raw is None else str(raw).strip()))
    ]
    return ", ".join(parts) or "—"


def _differences(before: DiplomaSnapshot, after: DiplomaSnapshot) -> tuple[FieldChange, ...]:
    """Поля, которыми снимки отличаются, — для отчёта, а не для решения.

    Решает :meth:`Diploma.differs_from`; это только показывает человеку, что
    именно он разрешает переписать.
    """
    changes: list[FieldChange] = []
    for field, label in _LABELS.items():
        was, now = getattr(before, field), getattr(after, field)
        if was != now:
            changes.append(FieldChange(field=label, before=_render(was), after=_render(now)))
    return tuple(changes)


class DiplomaSnapshotRefreshService:
    """Пересобирает снимки разошедшихся дипломов, не трогая остальные."""

    def __init__(
        self,
        *,
        repository: DiplomaRepository,
        snapshots: DiplomaSnapshotSource,
        workspace: PrintPackageWorkspace,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace

    def refresh(self, diplomas: Sequence[Diploma], *, now: datetime, apply: bool = False) -> list[RefreshOutcome]:
        """Сверить каждый диплом с его заявкой и, при ``apply``, перевыпустить разошедшиеся.

        Без ``apply`` не делается ни одной записи — это та же сверка, которой потом
        и выполняется работа, так что отчёт разведки описывает ровно то, что
        произойдёт.
        """
        # Заявка одна на несколько дипломов — у коллектива с поимённым составом их
        # столько, сколько детей. Пересобирается снимок по разу на заявку.
        built: dict[uuid.UUID, DiplomaSnapshot | None] = {}
        outcomes: list[RefreshOutcome] = []
        for diploma in diplomas:
            if diploma.submission_id not in built:
                build = self._snapshots.build(diploma.submission_id)
                built[diploma.submission_id] = build.snapshot if build is not None else None
            fresh = built[diploma.submission_id]
            if fresh is None:
                outcomes.append(self._skipped(diploma, "заявка удалена — пересобрать снимок не из чего"))
                continue
            if not diploma.differs_from(fresh):
                outcomes.append(
                    RefreshOutcome(diploma_id=diploma.id, number=diploma.number, recipient=diploma.recipient, status=RefreshStatus.UNCHANGED)
                )
                continue
            changes = _differences(diploma.snapshot, diploma.with_refreshed_snapshot(fresh, now=now).snapshot)
            if not apply:
                outcomes.append(
                    RefreshOutcome(
                        diploma_id=diploma.id,
                        number=diploma.number,
                        recipient=diploma.recipient,
                        status=RefreshStatus.PLANNED,
                        changes=changes,
                    )
                )
                continue
            outcomes.append(self._apply(diploma, fresh, changes=changes, now=now))
        return outcomes

    def _apply(self, diploma: Diploma, fresh: DiplomaSnapshot, *, changes: tuple[FieldChange, ...], now: datetime) -> RefreshOutcome:
        """Перевыпустить один диплом — целиком или никак."""
        updated = diploma.with_refreshed_snapshot(fresh, now=now)
        rerendered = False
        if diploma.official_pdf_path:
            assets = self._workspace.load_template(diploma.template_id)
            if assets is None:
                return self._skipped(diploma, "шаблон диплома недоступен — копию участника нечем перерисовать", changes=changes)
            try:
                data = self._workspace.render(
                    assets=assets,
                    snapshot=updated.snapshot,
                    number=updated.number,
                    verification_token=updated.verification_token,
                )
                # Тот же ключ хранилища (фестиваль + номер): ссылка, которая уже есть
                # у участника, после замены ведёт на обновлённый файл.
                path = self._workspace.store_official_pdf(competition_id=updated.competition_id, number=updated.number, data=data)
            # Широкий перехват намеренно: причина уходит в отчёт, и сбой одного
            # диплома не должен ронять пересборку остальных.
            except Exception as error:
                return self._skipped(diploma, f"не удалось перерисовать PDF: {error}", changes=changes)
            # `issued` сохраняет первоначальный `issued_at`: документ выпущен тогда,
            # когда выпущен, и перевыпуск не делает его новее для кабинета.
            updated = updated.issued(path, now=now)
            rerendered = True
        self._repository.update(updated)
        return RefreshOutcome(
            diploma_id=updated.id,
            number=updated.number,
            recipient=updated.recipient,
            status=RefreshStatus.UPDATED,
            changes=changes,
            rerendered=rerendered,
        )

    @staticmethod
    def _skipped(diploma: Diploma, reason: str, *, changes: tuple[FieldChange, ...] = ()) -> RefreshOutcome:
        return RefreshOutcome(
            diploma_id=diploma.id,
            number=diploma.number,
            recipient=diploma.recipient,
            status=RefreshStatus.SKIPPED,
            changes=changes,
            reason=reason,
        )
