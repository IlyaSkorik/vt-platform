"""Round-trip tests for the Programs persistence adapter (real PostgreSQL).

Build an aggregate through the domain, persist it, reload it, and assert the whole
graph survives - order above all, because the running order *is* the program. Also
covers what soft-deleting a child means for a public link.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.programs.domain.entities import Program, ProgramItem
from apps.programs.domain.value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    ArrangementBlock,
    ArrangementSettings,
    BreakRule,
    CellValue,
    ColumnTitle,
    GroupingAxis,
    ItemDuration,
    ItemTitle,
    PerformanceOrder,
    ProgramColumn,
    ProgramItemKind,
    ProgramItemProgress,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
)
from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel, ProgramShareModel
from apps.programs.infrastructure.repositories import DjangoProgramRepository

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
NOON = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()


def _program() -> Program:
    return Program.create(
        program_id=uuid.uuid4(),
        competition_id=COMPETITION_ID,
        name=ProgramName("Вокал, 1 отделение"),
        now=NOW,
        nomination_id=NOMINATION_ID,
        starts_at=TEN_AM,
        buffer=TimeBuffer(seconds=30),
    )


def _act(program: Program, seconds: int = 200) -> uuid.UUID:
    return program.add_performance(
        item_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        duration=ItemDuration(seconds),
        now=NOW,
    ).id


def _publish(program: Program, slug: str = "Screen234") -> None:
    """Publish an edition - the act that freezes the numbers."""
    program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug(slug), now=NOW)


def _break(program: Program, title: str = "Перерыв", seconds: int = 900) -> uuid.UUID:
    return program.add_block(
        item_id=uuid.uuid4(),
        kind=ProgramItemKind.BREAK,
        title=ItemTitle(title),
        duration=ItemDuration(seconds),
        now=NOW,
    ).id


class TestRoundTrip:
    def test_the_whole_aggregate_survives(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first = _act(program)
        pause = _break(program)
        second = _act(program, 240)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Программа звукорежиссёра"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ProgramColumn.TIME, ProgramColumn.TITLE, ProgramColumn.COMMENT],
            item_ids=[first, second],
        )
        repository.save(program)

        loaded = repository.get(program.id)
        assert loaded is not None
        assert str(loaded.name) == "Вокал, 1 отделение"
        assert loaded.competition_id == COMPETITION_ID
        assert loaded.nomination_id == NOMINATION_ID
        assert loaded.starts_at == TEN_AM
        assert loaded.buffer.seconds == 30
        assert [item.id for item in loaded.items] == [first, pause, second]
        assert [item.kind for item in loaded.items] == [
            ProgramItemKind.PERFORMANCE,
            ProgramItemKind.BREAK,
            ProgramItemKind.PERFORMANCE,
        ]
        assert str(loaded.item(pause).title) == "Перерыв"
        assert loaded.item(second).duration.seconds == 240
        assert [s.id for s in loaded.shares] == [share.id]
        assert loaded.shares[0].item_ids == (first, second)
        assert [ref.key for ref in loaded.shares[0].columns] == ["TIME", "TITLE", "COMMENT"]

    def test_the_order_is_the_order_that_comes_back(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second, third = _act(program), _act(program), _act(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        reloaded.reorder([third, first, second], now=NOW)
        repository.save(reloaded)

        assert [item.id for item in repository.get(program.id).items] == [third, first, second]  # type: ignore[union-attr]
        assert list(
            ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).order_by("position").values_list("id", flat=True)
        ) == [third, first, second]

    def test_the_frozen_flag_and_the_numbers_survive_a_reorder_across_a_reload(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second, third = _act(program), _act(program), _act(program)
        _publish(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert reloaded.numbers_frozen is True
        assert reloaded.numbers_frozen_at == NOW
        reloaded.reorder([first, third, second], now=NOW)
        repository.save(reloaded)

        again = repository.get(program.id)
        assert again is not None
        assert [item.id for item in again.items] == [first, third, second]
        assert [item.number for item in again.items] == [1, 3, 2]

    def test_an_unpublished_programme_reloads_unfrozen_and_still_renumbers(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program), _act(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert reloaded.numbers_frozen is False
        reloaded.reorder([second, first], now=NOW)
        repository.save(reloaded)

        again = repository.get(program.id)
        assert again is not None
        assert [item.id for item in again.items] == [second, first]
        assert [item.number for item in again.items] == [1, 2]

    def test_a_retired_number_is_not_reissued_after_a_reload(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _first, second = _act(program), _act(program)
        _publish(program)
        program.remove_item(second, now=NOW)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert (
            reloaded.add_performance(
                item_id=uuid.uuid4(),
                submission_id=uuid.uuid4(),
                duration=ItemDuration(200),
                now=NOW,
            ).number
            == 3
        )

    def test_a_row_written_before_numbers_existed_falls_back_to_its_ordinal(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program), _act(program)
        repository.save(program)
        ProgramItemModel.objects.filter(program_id=program.id).update(number=0)

        loaded = repository.get(program.id)
        assert loaded is not None
        assert [item.number for item in loaded.items] == [1, 2]
        assert [item.id for item in loaded.items] == [first, second]

    def test_a_performance_slot_stores_no_title(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        item_id = _act(program)
        repository.save(program)
        assert ProgramItemModel.objects.get(id=item_id).title == ""

    def test_a_removed_item_is_soft_deleted_not_dropped(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        item_id = _break(program)
        repository.save(program)
        program.remove_item(item_id, now=NOW)
        repository.save(program)

        assert repository.get(program.id).items == ()  # type: ignore[union-attr]
        assert ProgramItemModel.objects.get(id=item_id).deleted_at is not None

    def test_an_empty_program_persists(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        repository.save(program)
        loaded = repository.get(program.id)
        assert loaded is not None
        assert loaded.items == ()


class TestListing:
    def test_programs_are_listed_per_competition_and_nomination(self) -> None:
        repository = DjangoProgramRepository()
        vocals = _program()
        repository.save(vocals)
        other_nomination = Program.create(
            program_id=uuid.uuid4(),
            competition_id=COMPETITION_ID,
            name=ProgramName("Хореография"),
            now=NOW,
            nomination_id=uuid.uuid4(),
        )
        repository.save(other_nomination)
        elsewhere = Program.create(
            program_id=uuid.uuid4(),
            competition_id=uuid.uuid4(),
            name=ProgramName("Другой фестиваль"),
            now=NOW,
        )
        repository.save(elsewhere)

        assert len(repository.list_for_competition(competition_id=COMPETITION_ID)) == 2
        scoped = repository.list_for_competition(competition_id=COMPETITION_ID, nomination_id=NOMINATION_ID)
        assert [p.id for p in scoped] == [vocals.id]

    def test_a_deleted_program_disappears_from_reads(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        repository.save(program)
        program.delete(now=NOW)
        repository.save(program)

        assert repository.get(program.id) is None
        assert repository.list_for_competition(competition_id=COMPETITION_ID) == ()


class TestPublicLinks:
    def test_a_slug_resolves_to_its_program_and_edition(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)

        found = repository.get_by_slug("Screen234")
        assert found is not None
        loaded, share_id = found
        assert loaded.id == program.id
        assert share_id == share.id

    def test_an_unknown_slug_resolves_to_nothing(self) -> None:
        assert DjangoProgramRepository().get_by_slug("Nobody234") is None

    def test_a_revoked_edition_stops_resolving_but_keeps_its_slug_claimed(self) -> None:
        # A slug must never be handed out twice, or an old printed link would start
        # pointing at somebody else's programme.
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Временная"), slug=PublicSlug("Temp23456"), now=NOW)
        repository.save(program)
        program.remove_share(share.id, now=NOW)
        repository.save(program)

        assert repository.get_by_slug("Temp23456") is None
        assert repository.slug_taken("Temp23456") is True
        assert ProgramShareModel.objects.get(id=share.id).deleted_at is not None

    def test_deleting_the_program_takes_its_revoked_links_down(self) -> None:
        """The order the aggregate enforces: revoke, then delete — see ``Program.delete``."""
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)
        program.remove_share(share.id, now=NOW)
        program.delete(now=NOW)
        repository.save(program)

        assert repository.get_by_slug("Screen234") is None
        # The slug stays claimed: a printed link must never start pointing elsewhere.
        assert repository.slug_taken("Screen234") is True

    def test_a_free_slug_is_not_reported_as_taken(self) -> None:
        assert DjangoProgramRepository().slug_taken("Nobody234") is False

    def test_a_stamp_names_the_edition_and_the_version_it_was_read_at(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)

        stamp = repository.stamp_for_slug("Screen234")
        assert stamp == (share.id, program.version)

    def test_a_stamp_moves_when_the_programme_does(self) -> None:
        """What the public screen's validator is built on: it must move on every change."""
        repository = DjangoProgramRepository()
        program = _program()
        item_id = _act(program)
        program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)
        before = repository.stamp_for_slug("Screen234")

        program.set_item_progress(item_id, ProgramItemProgress.ON_STAGE, now=NOW)
        repository.save(program)

        assert repository.stamp_for_slug("Screen234") != before

    def test_a_stamp_follows_the_same_liveness_rules_as_the_link(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Временная"), slug=PublicSlug("Temp23456"), now=NOW)
        repository.save(program)
        program.remove_share(share.id, now=NOW)
        repository.save(program)

        assert repository.stamp_for_slug("Temp23456") is None
        assert repository.stamp_for_slug("Nobody234") is None

    def test_a_row_written_before_columns_existed_loads_with_the_defaults(self) -> None:
        """The columns field is JSON, so an older row simply has an empty list."""
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Старая ссылка"),
            slug=PublicSlug("Legacy234"),
            now=NOW,
            columns=[ProgramColumn.TIME],
        )
        repository.save(program)
        ProgramShareModel.objects.filter(id=share.id).update(columns=[])

        loaded = repository.get(program.id)
        assert loaded is not None
        assert [ref.key for ref in loaded.shares[0].columns] == [column.value for column in DEFAULT_PUBLIC_COLUMNS]


class TestGenerationRules:
    """The rules a programme was generated from survive a round trip (VT-86)."""

    def test_the_rules_are_stored_with_the_programme(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        settings = ArrangementSettings(
            grouping=(GroupingAxis.NOMINATION, GroupingAxis.AGE_CATEGORY),
            order_within_group=PerformanceOrder.DURATION_ASC,
            break_rule=BreakRule.EVERY_DURATION,
            break_after_seconds=5400,
            break_block=ArrangementBlock.of("Антракт", seconds=900),
            repeat_gap=3,
            opens_with=ArrangementBlock.of("Открытие", seconds=600),
        )
        program.rebuild(
            [ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(200))],
            settings=settings,
            now=NOW,
        )
        repository.save(program)

        reloaded = repository.get(program.id)

        assert reloaded is not None
        assert reloaded.arrangement == settings

    def test_a_hand_built_programme_carries_no_rules(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        repository.save(program)

        reloaded = repository.get(program.id)

        assert reloaded is not None
        assert reloaded.arrangement is None

    def test_rules_that_no_longer_make_sense_cost_a_refilled_dialog_not_the_programme(self) -> None:
        # These settings prefill a form; they are not programme data. A grouping axis
        # retired in a later release must never be what stops a programme from loading.
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        repository.save(program)
        ProgramModel.objects.filter(id=program.id).update(arrangement={"grouping": ["BY_THE_MOON"]})

        reloaded = repository.get(program.id)

        assert reloaded is not None
        assert reloaded.arrangement is None
        assert len(reloaded.items) == 1


class TestUndoingARebuild:
    """Reading back the running order a rebuild replaced (VT-86).

    The whole undo rests on one property of the adapter: a replaced slot is retired,
    not erased, and every row a single save retires carries that save's instant. These
    tests pin that property, because without it the undo silently restores nothing.
    """

    def _rules(self) -> ArrangementSettings:
        return ArrangementSettings(grouping=(GroupingAxis.NOMINATION,), order_within_group=PerformanceOrder.DURATION_ASC)

    def test_the_replaced_order_is_readable_at_the_instant_it_was_replaced(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program, 200), _act(program, 180)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        reloaded.rebuild(
            [ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(300))],
            settings=self._rules(),
            now=TEN_AM,
        )
        repository.save(reloaded)

        assert reloaded.rebuilt_at is not None
        retired = repository.items_retired_at(program.id, reloaded.rebuilt_at)

        assert [item.id for item in retired] == [first, second]

    def test_the_restore_point_survives_a_reload(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        repository.save(program)
        program.rebuild([], settings=self._rules(), now=TEN_AM)
        repository.save(program)

        reloaded = repository.get(program.id)

        assert reloaded is not None
        assert reloaded.rebuilt_at == TEN_AM
        assert reloaded.can_undo_rebuild

    def test_a_restored_slot_keeps_the_cells_that_were_filled_in_by_hand(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        item_id = _act(program)
        program.fill_cell(item_id=item_id, column_id=column.id, value=CellValue("радио, 2 шт"), now=NOW)
        repository.save(program)

        program.rebuild([], settings=self._rules(), now=TEN_AM)
        repository.save(program)

        assert program.rebuilt_at is not None
        retired = repository.items_retired_at(program.id, program.rebuilt_at)

        assert len(retired) == 1
        assert str(retired[0].value_in(column.id)) == "радио, 2 шт"

    def test_undoing_revives_the_original_rows_rather_than_writing_new_ones(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program, 200), _act(program, 180)
        repository.save(program)
        program.rebuild(
            [ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(300))],
            settings=self._rules(),
            now=TEN_AM,
        )
        repository.save(program)
        assert program.rebuilt_at is not None

        program.restore_order(repository.items_retired_at(program.id, program.rebuilt_at), now=NOON)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert [item.id for item in reloaded.items] == [first, second]
        # The same two rows came back; the generated one went the way they had gone.
        assert ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).count() == 2
        assert ProgramItemModel.objects.filter(program_id=program.id, id__in=[first, second], deleted_at__isnull=True).count() == 2

    def test_the_generated_order_becomes_its_own_restore_point(self) -> None:
        """So an undo pressed by mistake is itself recoverable - by the same mechanism."""
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        repository.save(program)
        program.rebuild(
            [ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(300))],
            settings=self._rules(),
            now=TEN_AM,
        )
        repository.save(program)
        assert program.rebuilt_at is not None
        program.restore_order(repository.items_retired_at(program.id, program.rebuilt_at), now=NOON)
        repository.save(program)

        assert len(repository.items_retired_at(program.id, NOON)) == 1
