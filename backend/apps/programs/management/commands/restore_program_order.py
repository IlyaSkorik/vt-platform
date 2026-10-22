"""``restore_program_order`` — вернуть программе её предыдущий состав строк.

Пересборка («Пересобрать») заменяет весь состав целиком: каждый слот новый, а
старые строки репозиторий не удаляет, а помечает ``deleted_at`` одним и тем же
моментом (см. ``DjangoProgramRepository._sync_items``). Поэтому каждая пересборка
оставляет в таблице цельный снимок того, что стояло до неё — эта команда их
показывает и умеет вернуть любой из них.

Возврат — такая же замена: нынешние живые строки уходят в ``deleted_at``, снимок
возвращается. Значит, и сам возврат создаёт точку возврата, и ошибиться им нельзя
необратимо.

Usage::

    python manage.py restore_program_order                                  # где вообще есть что возвращать
    python manage.py restore_program_order --program <uuid>                 # точки возврата одной программы
    python manage.py restore_program_order --program <uuid> --at <iso>      # что будет сделано (ничего не пишет)
    python manage.py restore_program_order --program <uuid> --at <iso> --apply
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.programs.infrastructure.models.program import ProgramItemModel, ProgramModel

#: Сколько строк снимка печатать целиком, прежде чем свернуть остаток в счётчик.
_PREVIEW_ROWS = 40


class Command(BaseCommand):
    """Показать точки возврата программы и вернуть одну из них."""

    help = "Restore a program's running order to the state it had before a rebuild."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--program", help="Program id (UUID). Omit to list programs that have restore points.")
        parser.add_argument("--search", help="Find the program by a fragment of its name instead of an id.")
        parser.add_argument("--at", help="Restore point to return to: the ISO timestamp from the listing.")
        parser.add_argument("--apply", action="store_true", help="Actually write. Without it the command only reports.")
        parser.add_argument("--force", action="store_true", help="Restore even though the program is published and its numbers are frozen.")

    def handle(self, *args: Any, **options: Any) -> None:
        if options.get("search"):
            self._search(str(options["search"]))
            return
        if not options.get("program"):
            self._list_programs()
            return

        program = self._program(str(options["program"]))
        if not options.get("at"):
            self._list_points(program)
            return

        self._restore(program, self._point(str(options["at"])), apply=bool(options["apply"]), force=bool(options["force"]))

    # ------------------------------------------------------------------
    # Поиск программы
    # ------------------------------------------------------------------

    def _search(self, fragment: str) -> None:
        rows = ProgramModel.objects.filter(name__icontains=fragment, deleted_at__isnull=True).order_by("-updated_at")[:20]
        if not rows:
            raise CommandError(f"Программ с «{fragment}» в названии не найдено.")
        for program in rows:
            points = self._points(program).count()
            self.stdout.write(f"{program.id}  {program.name}  (точек возврата: {points}, изменена {program.updated_at.isoformat()})")

    def _list_programs(self) -> None:
        """Программы, у которых вообще есть что возвращать — свежие сверху."""
        ids = ProgramItemModel.objects.filter(deleted_at__isnull=False).values_list("program_id", flat=True).distinct()
        rows = ProgramModel.objects.filter(id__in=list(ids), deleted_at__isnull=True).order_by("-updated_at")[:30]
        if not rows:
            self.stdout.write("Точек возврата нет ни у одной программы.")
            return
        self.stdout.write("Программы, у которых есть точки возврата (свежие сверху):\n")
        for program in rows:
            last = self._points(program).first()
            when = last.isoformat() if last else "—"
            self.stdout.write(f"{program.id}  {program.name}  последняя пересборка: {when}")
        self.stdout.write("\nДальше: --program <id>")

    def _program(self, raw: str) -> ProgramModel:
        try:
            program_id = uuid.UUID(raw)
        except ValueError as exc:
            raise CommandError(f"«{raw}» не UUID. Найти программу по названию: --search <часть названия>.") from exc
        program = ProgramModel.objects.filter(id=program_id).first()
        if program is None:
            raise CommandError(f"Программы {raw} нет.")
        return program

    # ------------------------------------------------------------------
    # Точки возврата
    # ------------------------------------------------------------------

    def _points(self, program: ProgramModel) -> Any:
        """Моменты пересборок этой программы, свежие сверху.

        Одна пересборка проставляет всем уходящим строкам один и тот же
        ``deleted_at``, поэтому различные значения столбца и есть снимки.
        """
        return (
            ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=False)
            .values_list("deleted_at", flat=True)
            .distinct()
            .order_by("-deleted_at")
        )

    def _list_points(self, program: ProgramModel) -> None:
        live = ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).count()
        self.stdout.write(f"Программа: {program.name} ({program.id})")
        self.stdout.write(f"Сейчас в ней строк: {live}")
        if program.numbers_frozen_at is not None:
            self.stdout.write(self.style.WARNING(f"Опубликована {program.numbers_frozen_at.isoformat()} — номера закреплены."))
        points = list(self._points(program))
        if not points:
            self.stdout.write("\nТочек возврата нет: программу ни разу не пересобирали.")
            return
        self.stdout.write("\nТочки возврата (свежие сверху):\n")
        for moment in points:
            count = ProgramItemModel.objects.filter(program_id=program.id, deleted_at=moment).count()
            self.stdout.write(f"  --at {moment.isoformat()}   строк в снимке: {count}")
        self.stdout.write("\nДальше: --at <timestamp> — покажет, что изменится; добавить --apply — применит.")

    def _point(self, raw: str) -> datetime:
        moment = parse_datetime(raw)
        if moment is None:
            raise CommandError(f"«{raw}» не разбирается как момент времени. Скопируйте значение из колонки --at в списке точек возврата.")
        if timezone.is_naive(moment):
            moment = timezone.make_aware(moment)
        return moment

    # ------------------------------------------------------------------
    # Возврат
    # ------------------------------------------------------------------

    def _restore(self, program: ProgramModel, moment: datetime, *, apply: bool, force: bool) -> None:
        snapshot = ProgramItemModel.objects.filter(program_id=program.id, deleted_at=moment).order_by("position")
        if not snapshot.exists():
            raise CommandError(f"На {moment.isoformat()} снимка нет. Точный момент — в списке: --program {program.id}")
        live = ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).order_by("position")

        if program.numbers_frozen_at is not None and not force:
            raise CommandError(
                f"Программа опубликована {program.numbers_frozen_at.isoformat()} — возврат изменит номера, уже названные участникам. "
                "Если это осознанное решение, повторите с --force."
            )

        self.stdout.write(f"Программа: {program.name} ({program.id})")
        self.stdout.write(f"\nВернуть снимок от {moment.isoformat()} — {snapshot.count()} строк:\n")
        self._print_rows(snapshot)
        self.stdout.write(f"\nУйдёт нынешний состав — {live.count()} строк (станет новой точкой возврата):\n")
        self._print_rows(live)

        if not apply:
            self.stdout.write(self.style.WARNING("\nНичего не записано. Повторите с --apply, чтобы применить."))
            return

        now = timezone.now()
        with transaction.atomic():
            # Нынешние строки уходят первыми: «одно выступление — одна строка» это
            # частичный уникальный индекс по живым строкам, и оба состава на
            # мгновение ссылаются на одни и те же выступления.
            retired = live.update(deleted_at=now, updated_at=now, version=F("version") + 1)
            restored = ProgramItemModel.objects.filter(program_id=program.id, deleted_at=moment).update(
                deleted_at=None,
                updated_at=now,
                version=F("version") + 1,
            )
            # Версия корня — пре-образ оптимистической блокировки: вкладка,
            # открытая до возврата, получит внятный конфликт вместо того, чтобы
            # молча записать поверх восстановленного.
            #
            # ``rebuilt_at`` гасится здесь же, и это не уборка, а необходимость:
            # кнопка «Отменить пересборку» ищет строки по этому моменту, а сейчас они
            # снова живые — она нашла бы пустоту и опустошила программу. Возврат
            # вручную точку возврата тратит, как и обычная отмена.
            ProgramModel.objects.filter(id=program.id).update(updated_at=now, rebuilt_at=None, version=F("version") + 1)

        self.stdout.write(self.style.SUCCESS(f"\nГотово: вернулось {restored} строк, прежние {retired} ушли в точку возврата {now.isoformat()}."))
        self.stdout.write("Организатору: обновить страницу программы (F5) — вкладка, открытая до возврата, покажет конфликт версий.")

    def _print_rows(self, rows: Any) -> None:
        for item in rows[:_PREVIEW_ROWS]:
            what = item.title or (f"выступление {str(item.submission_id)[:8]}" if item.submission_id else item.kind)
            filled = f"  ячейки: {len(item.custom_values)}" if item.custom_values else ""
            self.stdout.write(f"  {item.position:>3}. №{item.number:<4} {what}  {item.duration_seconds} с{filled}")
        extra = rows.count() - _PREVIEW_ROWS
        if extra > 0:
            self.stdout.write(f"  … и ещё {extra}")
