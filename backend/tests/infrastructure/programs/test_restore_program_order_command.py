"""Tests for the ``restore_program_order`` rescue command.

The command exists for what the in-app undo cannot reach: a programme rebuilt before
the restore point was recorded, or a snapshot older than the last one. It writes
directly to the tables, so these tests pin the two things that make that safe - the
order the two updates run in, and that it leaves no stale restore point behind.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.programs.domain.entities import Program, ProgramItem
from apps.programs.domain.value_objects import ArrangementSettings, ItemDuration, ProgramName, PublicSlug, ShareName
from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel
from apps.programs.infrastructure.repositories import DjangoProgramRepository

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


def _program() -> Program:
    return Program.create(
        program_id=uuid.uuid4(),
        competition_id=uuid.uuid4(),
        name=ProgramName("Вокал, 1 отделение"),
        now=NOW,
    )


def _act(program: Program, seconds: int = 200) -> uuid.UUID:
    return program.add_performance(
        item_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        duration=ItemDuration(seconds),
        now=NOW,
    ).id


def _rebuilt() -> tuple[Program, list[uuid.UUID]]:
    """A programme whose two hand-made slots were replaced by one generated one."""
    repository = DjangoProgramRepository()
    program = _program()
    before = [_act(program, 200), _act(program, 180)]
    repository.save(program)
    program.rebuild(
        [ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(300))],
        settings=ArrangementSettings(),
        now=TEN_AM,
    )
    repository.save(program)
    return program, before


def _run(*args: str) -> str:
    out = io.StringIO()
    call_command("restore_program_order", *args, stdout=out)
    return out.getvalue()


class TestListing:
    def test_the_restore_points_are_listed_with_the_size_of_each_snapshot(self) -> None:
        program, _ = _rebuilt()

        output = _run("--program", str(program.id))

        assert TEN_AM.isoformat() in output
        assert "строк в снимке: 2" in output

    def test_a_programme_never_rebuilt_says_so_rather_than_printing_nothing(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        repository.save(program)

        assert "Точек возврата нет" in _run("--program", str(program.id))

    def test_a_programme_is_findable_by_a_fragment_of_its_name(self) -> None:
        program, _ = _rebuilt()

        assert str(program.id) in _run("--search", "Вокал")

    def test_something_that_is_not_an_id_says_how_to_search_instead(self) -> None:
        with pytest.raises(CommandError, match="--search"):
            _run("--program", "не-uuid")


class TestRestoring:
    def test_without_apply_it_reports_and_writes_nothing(self) -> None:
        program, _ = _rebuilt()

        output = _run("--program", str(program.id), "--at", TEN_AM.isoformat())

        assert "Ничего не записано" in output
        assert ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).count() == 1

    def test_applying_revives_the_original_rows_and_retires_the_generated_one(self) -> None:
        program, before = _rebuilt()

        _run("--program", str(program.id), "--at", TEN_AM.isoformat(), "--apply")

        live = ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).order_by("position")
        assert [row.id for row in live] == before

    def test_the_restore_leaves_no_stale_undo_behind(self) -> None:
        # The app's «Отменить пересборку» looks for rows at ``rebuilt_at``; those rows
        # are live again, so leaving the stamp would make the button empty the programme.
        program, _ = _rebuilt()

        _run("--program", str(program.id), "--at", TEN_AM.isoformat(), "--apply")

        reloaded = DjangoProgramRepository().get(program.id)
        assert reloaded is not None
        assert reloaded.rebuilt_at is None
        assert not reloaded.can_undo_rebuild
        assert ProgramModel.objects.get(id=program.id).rebuilt_at is None

    def test_the_replaced_state_becomes_its_own_restore_point(self) -> None:
        program, _ = _rebuilt()

        _run("--program", str(program.id), "--at", TEN_AM.isoformat(), "--apply")

        points = ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=False).values_list("deleted_at", flat=True)
        assert len(set(points)) == 1
        assert TEN_AM not in set(points)

    def test_a_published_programme_is_refused_unless_forced(self) -> None:
        program, before = _rebuilt()
        program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        DjangoProgramRepository().save(program)

        with pytest.raises(CommandError, match="--force"):
            _run("--program", str(program.id), "--at", TEN_AM.isoformat(), "--apply")

        _run("--program", str(program.id), "--at", TEN_AM.isoformat(), "--apply", "--force")

        live = ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).order_by("position")
        assert [row.id for row in live] == before

    def test_a_moment_with_no_snapshot_is_refused_rather_than_emptying_the_programme(self) -> None:
        program, _ = _rebuilt()

        with pytest.raises(CommandError, match="снимка нет"):
            _run("--program", str(program.id), "--at", NOW.isoformat(), "--apply")

        assert ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).count() == 1
