"""``refresh_diploma_snapshots`` — перевыпустить дипломы, разошедшиеся с заявками.

Диплом печатается из замороженного снимка, снятого в момент его создания. Если
организатор исправил заявку позже — вписал учреждение за участника, поправил
фамилию, — исправление не попадает никуда: ни в PDF, ни в кабинет, ни на страницу
проверки по QR. Эта команда сверяет снимки с заявками и пересобирает те, что
разошлись.

**Ничего не пишет, пока не сказано ``--apply``.** Сначала отчёт: какие дипломы
разошлись и чем именно — поле, было, стало. Разведка и запись идут по одной и той
же сверке, поэтому отчёт описывает ровно то, что произойдёт.

**Совпавшие дипломы не трогаются вовсе** — ни записи, ни рендера, ни нового
``version``. Это главное свойство команды: реестр документов остаётся журналом
того, что действительно менялось.

Номер, токен проверки и идентификатор сохраняются, поэтому напечатанный QR
продолжает работать и ведёт на исправленные данные. Копия участника
перерисовывается по тому же ключу хранилища — ссылка, которая у него уже есть,
не меняется. Печатный бланк не трогается: он давно распечатан.

Usage::

    python manage.py refresh_diploma_snapshots                                # где вообще есть расхождения
    python manage.py refresh_diploma_snapshots --competition <uuid>           # что изменится у фестиваля
    python manage.py refresh_diploma_snapshots --competition <uuid> --apply   # перевыпустить
    python manage.py refresh_diploma_snapshots --number VT-2026-0007 --apply  # точечно, один диплом
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.diplomas.application.refresh import RefreshOutcome, RefreshStatus
from apps.diplomas.composition import build_diploma_snapshot_refresh_service
from apps.diplomas.infrastructure.models import DiplomaModel
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository

#: Сколько расхождений печатать подробно, прежде чем свернуть остаток в счётчик.
_PREVIEW_ROWS = 60


class Command(BaseCommand):
    """Сверить дипломы с заявками и перевыпустить разошедшиеся."""

    help = "Rebuild the frozen snapshot of diplomas whose submission data has since changed."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--competition", help="Фестиваль (UUID). Без него — обзор по всем фестивалям.")
        parser.add_argument("--number", help="Один диплом по номеру из реестра. Можно указать несколько через запятую.")
        parser.add_argument("--apply", action="store_true", help="Записать. Без этого команда только показывает.")

    def handle(self, *args: Any, **options: Any) -> None:
        apply = bool(options["apply"])
        if options.get("number"):
            self._run(self._by_numbers(str(options["number"])), apply=apply)
            return
        if options.get("competition"):
            self._run(self._by_competition(str(options["competition"])), apply=apply)
            return
        if apply:
            # Запись сразу по всем фестивалям — не та команда, которую стоит уметь
            # запустить одним словом: за ней стоят чужие выданные документы.
            raise CommandError("Укажите --competition или --number: массовая запись по всем фестивалям сразу не делается.")
        self._overview()

    # ------------------------------------------------------------------
    # Выборки
    # ------------------------------------------------------------------

    def _by_competition(self, raw: str) -> list[Any]:
        competition_id = self._uuid(raw, "фестиваля")
        diplomas = DjangoDiplomaRepository().list_by_competition(competition_id)
        if not diplomas:
            raise CommandError(f"У фестиваля {competition_id} нет дипломов.")
        return diplomas

    def _by_numbers(self, raw: str) -> list[Any]:
        numbers = [number.strip() for number in raw.split(",") if number.strip()]
        rows = list(DiplomaModel.objects.filter(number__in=numbers, deleted_at__isnull=True).values_list("id", flat=True))
        if not rows:
            raise CommandError(f"Дипломов с номерами {', '.join(numbers)} не найдено.")
        repository = DjangoDiplomaRepository()
        found = [diploma for diploma_id in rows if (diploma := repository.get(diploma_id)) is not None]
        if len(found) < len(numbers):
            missing = sorted(set(numbers) - {diploma.number for diploma in found})
            self.stdout.write(self.style.WARNING(f"Не найдены: {', '.join(missing)}"))
        return found

    def _overview(self) -> None:
        """Обзор: у каких фестивалей вообще есть что перевыпускать."""
        competition_ids = list(DiplomaModel.objects.filter(deleted_at__isnull=True).values_list("competition_id", flat=True).distinct())
        if not competition_ids:
            self.stdout.write("Дипломов пока нет.")
            return
        service = build_diploma_snapshot_refresh_service()
        repository = DjangoDiplomaRepository()
        now = timezone.now()
        total = 0
        for competition_id in competition_ids:
            outcomes = service.refresh(repository.list_by_competition(competition_id), now=now, apply=False)
            planned = [outcome for outcome in outcomes if outcome.status is RefreshStatus.PLANNED]
            skipped = [outcome for outcome in outcomes if outcome.status is RefreshStatus.SKIPPED]
            total += len(planned)
            if not planned and not skipped:
                continue
            self.stdout.write(f"{competition_id}  дипломов: {len(outcomes)}, разошлись: {len(planned)}, не перевыпустить: {len(skipped)}")
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Расхождений нет — все дипломы совпадают со своими заявками."))
            return
        self.stdout.write("")
        self.stdout.write(f"Всего разошлось: {total}. Для подробностей: --competition <uuid>")

    # ------------------------------------------------------------------
    # Работа
    # ------------------------------------------------------------------

    def _run(self, diplomas: list[Any], *, apply: bool) -> None:
        outcomes = build_diploma_snapshot_refresh_service().refresh(diplomas, now=timezone.now(), apply=apply)
        unchanged = [outcome for outcome in outcomes if outcome.status is RefreshStatus.UNCHANGED]
        touched = [outcome for outcome in outcomes if outcome.status in {RefreshStatus.PLANNED, RefreshStatus.UPDATED}]
        skipped = [outcome for outcome in outcomes if outcome.status is RefreshStatus.SKIPPED]

        for outcome in touched[:_PREVIEW_ROWS]:
            self._print(outcome)
        if len(touched) > _PREVIEW_ROWS:
            self.stdout.write(f"… и ещё {len(touched) - _PREVIEW_ROWS}")

        for outcome in skipped:
            self.stdout.write(self.style.WARNING(f"[пропуск] {self._title(outcome)}: {outcome.reason}"))

        self.stdout.write("")
        self.stdout.write(f"Совпадают (не тронуты): {len(unchanged)}")
        rerendered = sum(1 for outcome in touched if outcome.rerendered)
        if apply:
            self.stdout.write(self.style.SUCCESS(f"Перевыпущено: {len(touched)} (из них перерисовано PDF: {rerendered})"))
        elif touched:
            self.stdout.write(f"Разошлись: {len(touched)}. Запуск с --apply перевыпустит их.")
        else:
            self.stdout.write(self.style.SUCCESS("Расхождений нет — трогать нечего."))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Не перевыпустить: {len(skipped)} — см. причины выше."))

    def _print(self, outcome: RefreshOutcome) -> None:
        self.stdout.write(self._title(outcome))
        for change in outcome.changes:
            self.stdout.write(f"    {change.field}: {change.before} → {change.after}")

    @staticmethod
    def _title(outcome: RefreshOutcome) -> str:
        suffix = f" ({outcome.recipient})" if outcome.recipient else ""
        return f"{outcome.number}{suffix}"

    @staticmethod
    def _uuid(raw: str, what: str) -> uuid.UUID:
        try:
            return uuid.UUID(raw)
        except ValueError as error:
            raise CommandError(f"Неверный идентификатор {what}: {raw}") from error
