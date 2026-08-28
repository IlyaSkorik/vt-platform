"""Unit tests for the ``Program`` aggregate and its value objects.

Covers what the aggregate refuses as much as what it allows: the running order is the
thing the whole day is run from, so an act cannot be doubled, a reorder cannot lose a
slot, and a public edition cannot point at something that is not in the program.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.programs.domain.entities import Program, ProgramItem, ProgramShare
from apps.programs.domain.exceptions import (
    InvalidProgramDataError,
    ItemNotInProgramError,
    PerformanceAlreadyInProgramError,
    ProgramColumnNotFoundError,
    ProgramItemNotFoundError,
    ProgramShareNotFoundError,
    ReorderMismatchError,
)
from apps.programs.domain.value_objects import (
    COLUMN_LABELS,
    DEFAULT_PUBLIC_COLUMNS,
    CellValue,
    ColumnRef,
    ColumnTitle,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
    ProgramItemProgress,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
    parse_columns,
)

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


def _program(**kwargs: object) -> Program:
    return Program.create(
        program_id=uuid.uuid4(),
        competition_id=uuid.uuid4(),
        name=ProgramName("Вокал, 1 отделение"),
        now=NOW,
        **kwargs,  # type: ignore[arg-type]
    )


def _add_act(program: Program, seconds: int = 200) -> ProgramItem:
    return program.add_performance(
        item_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        duration=ItemDuration(seconds),
        now=NOW,
    )


def _add_break(program: Program, seconds: int = 900, *, position: int | None = None) -> ProgramItem:
    return program.add_block(
        item_id=uuid.uuid4(),
        kind=ProgramItemKind.BREAK,
        title=ItemTitle("Перерыв"),
        duration=ItemDuration(seconds),
        now=NOW,
        position=position,
    )


class TestCreation:
    def test_a_new_program_is_empty_and_unbuffered(self) -> None:
        program = _program()
        assert program.items == ()
        assert program.shares == ()
        assert program.buffer.seconds == 0
        assert program.starts_at is None

    def test_a_program_may_span_the_whole_competition(self) -> None:
        assert _program().nomination_id is None

    def test_a_program_is_usually_scoped_to_one_nomination(self) -> None:
        nomination_id = uuid.uuid4()
        assert _program(nomination_id=nomination_id).nomination_id == nomination_id

    def test_the_constructor_cannot_be_called_directly(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            Program(
                _token=object(),
                _id=uuid.uuid4(),
                _competition_id=uuid.uuid4(),
                _name=ProgramName("x"),
                _created_at=NOW,
                _updated_at=NOW,
            )

    def test_a_blank_name_is_rejected(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ProgramName("   ")


class TestItems:
    def test_acts_and_blocks_append_in_order(self) -> None:
        program = _program()
        first = _add_act(program)
        pause = _add_break(program)
        second = _add_act(program)
        assert [item.id for item in program.items] == [first.id, pause.id, second.id]

    def test_a_block_can_be_inserted_at_a_position(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        pause = _add_break(program, position=2)
        assert [item.id for item in program.items] == [first.id, pause.id, second.id]

    def test_an_out_of_range_position_clamps_instead_of_failing(self) -> None:
        program = _program()
        first = _add_act(program)
        pause = _add_break(program, position=99)
        assert [item.id for item in program.items] == [first.id, pause.id]

    def test_one_act_gets_one_slot(self) -> None:
        program = _program()
        submission_id = uuid.uuid4()
        program.add_performance(item_id=uuid.uuid4(), submission_id=submission_id, duration=ItemDuration(200), now=NOW)
        with pytest.raises(PerformanceAlreadyInProgramError):
            program.add_performance(item_id=uuid.uuid4(), submission_id=submission_id, duration=ItemDuration(200), now=NOW)

    def test_a_performance_slot_carries_no_title_of_its_own(self) -> None:
        # Its name is read from the act, so a corrected name shows up everywhere.
        program = _program()
        assert _add_act(program).title is None

    def test_a_performance_slot_cannot_be_retitled(self) -> None:
        program = _program()
        item = _add_act(program)
        with pytest.raises(InvalidProgramDataError):
            program.edit_item(item.id, now=NOW, title=ItemTitle("Своё название"))

    def test_a_block_can_be_retitled_and_resized(self) -> None:
        program = _program()
        item = _add_break(program)
        program.edit_item(item.id, now=NOW, title=ItemTitle("Обед"), duration=ItemDuration(2400))
        assert str(program.item(item.id).title) == "Обед"
        assert program.item(item.id).duration.seconds == 2400

    def test_a_slot_can_be_removed(self) -> None:
        program = _program()
        item = _add_break(program)
        program.remove_item(item.id, now=NOW)
        assert program.items == ()

    def test_removing_an_unknown_slot_is_an_error(self) -> None:
        program = _program()
        with pytest.raises(ProgramItemNotFoundError):
            program.remove_item(uuid.uuid4(), now=NOW)

    def test_a_zero_length_slot_is_rejected(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ItemDuration(0)


class TestReorder:
    def test_a_full_permutation_is_applied(self) -> None:
        program = _program()
        first, second, third = _add_act(program), _add_act(program), _add_act(program)
        program.reorder([third.id, first.id, second.id], now=NOW)
        assert [item.id for item in program.items] == [third.id, first.id, second.id]

    def test_a_reorder_that_drops_an_item_is_refused_whole(self) -> None:
        program = _program()
        first, _second = _add_act(program), _add_act(program)
        with pytest.raises(ReorderMismatchError):
            program.reorder([first.id], now=NOW)

    def test_a_reorder_that_invents_an_item_is_refused(self) -> None:
        program = _program()
        first = _add_act(program)
        with pytest.raises(ReorderMismatchError):
            program.reorder([first.id, uuid.uuid4()], now=NOW)

    def test_a_reorder_that_repeats_an_item_is_refused(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        with pytest.raises(ReorderMismatchError):
            program.reorder([first.id, first.id, second.id], now=NOW)


def _publish(program: Program, slug: str = "Sound2345") -> ProgramShare:
    """Publish an edition - the act that freezes the numbers."""
    return program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug(slug), now=NOW)


class TestNumbersWhileTheProgrammeIsBeingAssembled:
    """Nobody has been told a number yet, so numbers simply follow the running order."""

    def test_a_new_programme_is_not_frozen(self) -> None:
        program = _program()
        assert program.numbers_frozen is False
        assert program.numbers_frozen_at is None

    def test_slots_are_numbered_in_order_as_they_are_added(self) -> None:
        program = _program()
        assert [_add_act(program).number for _ in range(3)] == [1, 2, 3]

    def test_reordering_renumbers_freely(self) -> None:
        program = _program()
        first, second, third = _add_act(program), _add_act(program), _add_act(program)
        program.reorder([third.id, first.id, second.id], now=NOW)

        assert [item.number for item in program.items] == [1, 2, 3]
        assert [item.id for item in program.items] == [third.id, first.id, second.id]

    def test_a_block_inserted_in_the_middle_pushes_the_rest_along(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        pause = _add_break(program, position=2)

        assert [item.id for item in program.items] == [first.id, pause.id, second.id]
        assert [item.number for item in program.items] == [1, 2, 3]

    def test_removing_a_slot_closes_the_gap(self) -> None:
        program = _program()
        first, second, third = _add_act(program), _add_act(program), _add_act(program)
        program.remove_item(second.id, now=NOW)

        assert [item.id for item in program.items] == [first.id, third.id]
        assert [item.number for item in program.items] == [1, 2]


class TestNumbersAfterTheFirstPublication:
    """Publishing is the moment numbers leave the organizer's screen, so they freeze."""

    def test_publishing_freezes_the_numbers(self) -> None:
        program = _program()
        _add_act(program)
        _publish(program)

        assert program.numbers_frozen is True
        assert program.numbers_frozen_at == NOW

    def test_reordering_then_moves_the_rows_and_leaves_the_numbers(self) -> None:
        # The case this exists for: a participant asks to perform later, so #4 is swapped
        # with #5 - and the programme legitimately reads 2, 3, 5, 4.
        program = _program()
        items = [_add_act(program) for _ in range(5)]
        _publish(program)
        first, second, third, fourth, fifth = items
        program.reorder([second.id, third.id, fifth.id, fourth.id, first.id], now=NOW)

        assert [item.number for item in program.items] == [2, 3, 5, 4, 1]

    def test_a_slot_added_after_publication_takes_the_next_free_number(self) -> None:
        program = _program()
        _add_act(program), _add_act(program)
        _publish(program)

        assert _add_act(program).number == 3

    def test_a_block_inserted_after_publication_pushes_nobody_number(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        _publish(program)
        pause = _add_break(program, position=2)

        assert [item.id for item in program.items] == [first.id, pause.id, second.id]
        assert [item.number for item in program.items] == [1, 3, 2]

    def test_a_removed_number_is_retired_rather_than_reused(self) -> None:
        # Handing номер 2 to somebody else after telling it to a participant is exactly
        # the confusion freezing exists to prevent.
        program = _program()
        _first, second = _add_act(program), _add_act(program)
        _publish(program)
        program.remove_item(second.id, now=NOW)

        assert _add_act(program).number == 3

    def test_a_second_publication_does_not_re_freeze(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        _publish(program, "Sound2345")
        program.reorder([second.id, first.id], now=NOW)
        _publish(program, "Screen234")

        # Re-freezing here would renumber what the first link already published.
        assert [item.number for item in program.items] == [2, 1]

    def test_renumbering_is_available_as_a_deliberate_reset(self) -> None:
        program = _program()
        items = [_add_act(program) for _ in range(3)]
        _publish(program)
        program.reorder([items[2].id, items[0].id, items[1].id], now=NOW)
        assert [item.number for item in program.items] == [3, 1, 2]

        program.renumber_sequentially(now=NOW)
        assert [item.number for item in program.items] == [1, 2, 3]

    def test_renumbering_frees_the_numbers_it_reclaimed(self) -> None:
        program = _program()
        first, second, third = _add_act(program), _add_act(program), _add_act(program)
        _publish(program)
        program.remove_item(third.id, now=NOW)
        program.renumber_sequentially(now=NOW)

        assert [item.number for item in program.items] == [1, 2]
        assert [item.id for item in program.items] == [first.id, second.id]
        assert _add_act(program).number == 3


class TestSettings:
    def test_the_buffer_can_be_changed_without_touching_any_act(self) -> None:
        program = _program()
        item = _add_act(program, 200)
        program.set_buffer(TimeBuffer(seconds=45), now=NOW)
        assert program.buffer.seconds == 45
        assert program.item(item.id).duration.seconds == 200

    def test_a_negative_buffer_is_rejected(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            TimeBuffer(seconds=-1)

    def test_the_start_time_can_be_set_and_cleared(self) -> None:
        program = _program()
        program.set_start(TEN_AM, now=NOW)
        assert program.starts_at == TEN_AM
        program.set_start(None, now=NOW)
        assert program.starts_at is None

    def test_every_edit_bumps_the_version_for_optimistic_concurrency(self) -> None:
        program = _program()
        before = program.version
        program.rename(ProgramName("Хореография"), now=NOW)
        assert program.version == before + 1
        assert program.initial_version == 1


class TestPublicEditions:
    def test_a_selection_is_published_behind_its_own_slug(self) -> None:
        program = _program()
        first, second, _third = _add_act(program), _add_act(program), _add_act(program)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Программа звукорежиссёра"),
            slug=PublicSlug("AbX82Kmn"),
            now=NOW,
            item_ids=[first.id, second.id],
        )
        assert [item.id for item in program.items_for(share)] == [first.id, second.id]
        assert share.covers_whole_program is False

    def test_an_empty_selection_follows_the_whole_program_as_it_grows(self) -> None:
        # The screen by the stage: published once, still correct after another act
        # is added.
        program = _program()
        _add_act(program)
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран у сцены"), slug=PublicSlug("Screen234"), now=NOW)
        _add_act(program)
        assert share.covers_whole_program is True
        assert len(program.items_for(share)) == 2

    def test_a_selection_follows_the_programs_current_order(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Для ведущего"),
            slug=PublicSlug("Host23456"),
            now=NOW,
            item_ids=[first.id, second.id],
        )
        program.reorder([second.id, first.id], now=NOW)
        assert [item.id for item in program.items_for(share)] == [second.id, first.id]

    def test_a_removed_item_simply_stops_appearing(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Для жюри"),
            slug=PublicSlug("Jury23456"),
            now=NOW,
            item_ids=[first.id, second.id],
        )
        program.remove_item(first.id, now=NOW)
        assert [item.id for item in program.items_for(share)] == [second.id]

    def test_a_share_cannot_select_a_foreign_item(self) -> None:
        program = _program()
        _add_act(program)
        with pytest.raises(ItemNotInProgramError):
            program.add_share(
                share_id=uuid.uuid4(),
                name=ShareName("Чужое"),
                slug=PublicSlug("Foreign234"),
                now=NOW,
                item_ids=[uuid.uuid4()],
            )

    def test_a_share_can_be_revoked(self) -> None:
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Временная"), slug=PublicSlug("Temp23456"), now=NOW)
        program.remove_share(share.id, now=NOW)
        assert program.shares == ()
        with pytest.raises(ProgramShareNotFoundError):
            program.share(share.id)

    def test_many_editions_of_one_program_coexist(self) -> None:
        program = _program()
        item = _add_act(program)
        for slug, name in (("Sound2345", "Звукорежиссёр"), ("Host23456", "Ведущий"), ("Jury23456", "Жюри"), ("Screen234", "Экран")):
            program.add_share(
                share_id=uuid.uuid4(),
                name=ShareName(name),
                slug=PublicSlug(slug),
                now=NOW,
                item_ids=[item.id],
            )
        assert len(program.shares) == 4


class TestPublishedColumns:
    """An edition is defined by which columns of the table it shows."""

    def test_an_edition_without_a_choice_shows_the_default_columns(self) -> None:
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        assert [ref.key for ref in share.columns] == [column.value for column in DEFAULT_PUBLIC_COLUMNS]

    def test_columns_are_kept_in_canonical_order(self) -> None:
        program = _program()
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Звукорежиссёр"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ProgramColumn.COMMENT, ProgramColumn.TITLE, ProgramColumn.TIME],
        )
        assert [ref.key for ref in share.columns] == ["TIME", "TITLE", "COMMENT"]

    def test_columns_can_be_changed_later_and_the_slug_survives(self) -> None:
        program = _program()
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Ведущий"),
            slug=PublicSlug("Host23456"),
            now=NOW,
            columns=[ProgramColumn.TIME],
        )
        program.set_share_columns(share.id, [ProgramColumn.TIME, ProgramColumn.PARTICIPANT], now=NOW)
        assert [ref.key for ref in program.share(share.id).columns] == ["TIME", "PARTICIPANT"]
        assert str(program.share(share.id).slug) == "Host23456"

    def test_two_editions_of_one_program_show_different_columns(self) -> None:
        # The point of the whole mechanism: one running order, many audiences.
        program = _program()
        engineer = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Звукорежиссёр"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ProgramColumn.TIME, ProgramColumn.TITLE, ProgramColumn.COMMENT],
        )
        screen = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Экран"),
            slug=PublicSlug("Screen234"),
            now=NOW,
            columns=[ProgramColumn.TIME, ProgramColumn.PARTICIPANT, ProgramColumn.TITLE],
        )
        assert ColumnRef.of(ProgramColumn.COMMENT) in engineer.columns
        assert ColumnRef.of(ProgramColumn.COMMENT) not in screen.columns

    def test_parsing_accepts_names_and_rejects_unknown_ones(self) -> None:
        assert parse_columns(["time", "TITLE"]) == (ProgramColumn.TIME, ProgramColumn.TITLE)
        assert parse_columns([]) == ()
        with pytest.raises(InvalidProgramDataError):
            parse_columns(["NOT_A_COLUMN"])

    def test_parsing_drops_duplicates(self) -> None:
        assert parse_columns(["TIME", "TIME", "TITLE"]) == (ProgramColumn.TIME, ProgramColumn.TITLE)

    def test_every_column_has_a_header(self) -> None:
        assert {column: COLUMN_LABELS[column] for column in ProgramColumn}
        assert COLUMN_LABELS[ProgramColumn.PARTICIPANT_GROUP] == "Состав участников"


class TestPrintedColumns:
    """A printed cut is laid out by the person printing it, not by the programme.

    The counterpart of the class above, and the two rules live side by side on purpose: a
    published edition keeps a column in the same place on every screen, while a page taken
    to the sound desk or to the register is ordered for the job it is doing there.
    """

    def test_a_selection_is_taken_in_the_order_it_was_given(self) -> None:
        program = _program()
        chosen = program.select_columns([ProgramColumn.COMMENT, ProgramColumn.TITLE, ProgramColumn.TIME])
        assert [ref.key for ref in chosen] == ["COMMENT", "TITLE", "TIME"]

    def test_the_same_selection_is_still_canonical_for_a_published_edition(self) -> None:
        program = _program()
        published = program.normalize_columns([ProgramColumn.COMMENT, ProgramColumn.TITLE, ProgramColumn.TIME])
        assert [ref.key for ref in published] == ["TIME", "TITLE", "COMMENT"]

    def test_a_column_named_twice_collapses_onto_its_first_mention(self) -> None:
        # A table cannot carry the same column in two places.
        program = _program()
        chosen = program.select_columns([ProgramColumn.TITLE, ProgramColumn.TIME, ProgramColumn.TITLE])
        assert [ref.key for ref in chosen] == ["TITLE", "TIME"]

    def test_a_custom_column_this_programme_has_not_got_is_refused(self) -> None:
        program = _program()
        with pytest.raises(ProgramColumnNotFoundError):
            program.select_columns([ColumnRef.custom(uuid.uuid4())])

    def test_a_custom_column_of_this_programme_keeps_its_chosen_place(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        chosen = program.select_columns([column.ref, ColumnRef.of(ProgramColumn.TITLE)])
        assert [ref.key for ref in chosen] == [column.ref.key, "TITLE"]


class TestCustomColumns:
    """The escape hatch: a column the organizer names and fills in themselves."""

    def test_a_custom_column_is_appended_after_the_built_in_ones(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)

        assert [c.id for c in program.custom_columns] == [column.id]
        assert program.columns[-1] == column.ref
        assert program.columns[0] == ColumnRef.of(ProgramColumn.POSITION)

    def test_a_blank_title_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ColumnTitle("   ")

    def test_a_cell_is_filled_and_cleared(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        item = _add_act(program)

        program.fill_cell(item_id=item.id, column_id=column.id, value=CellValue("  на стойке  "), now=NOW)
        assert str(program.item(item.id).value_in(column.id)) == "на стойке"

        # Blank is how a value is removed - no second verb for it.
        program.fill_cell(item_id=item.id, column_id=column.id, value=CellValue(""), now=NOW)
        assert program.item(item.id).value_in(column.id).is_blank

    def test_an_unfilled_cell_reads_blank_rather_than_missing(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Реквизит"), now=NOW)
        assert _add_act(program).value_in(column.id).is_blank

    def test_filling_an_unknown_column_is_refused(self) -> None:
        program = _program()
        item = _add_act(program)
        with pytest.raises(ProgramColumnNotFoundError):
            program.fill_cell(item_id=item.id, column_id=uuid.uuid4(), value=CellValue("x"), now=NOW)

    def test_renaming_keeps_the_values(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        item = _add_act(program)
        program.fill_cell(item_id=item.id, column_id=column.id, value=CellValue("на стойке"), now=NOW)

        program.rename_custom_column(column.id, ColumnTitle("Микрофон (тип)"), now=NOW)
        assert str(program.custom_column(column.id).title) == "Микрофон (тип)"
        assert str(program.item(item.id).value_in(column.id)) == "на стойке"

    def test_removing_a_column_takes_its_values_and_its_place_on_every_link(self) -> None:
        # Leaving a published edition pointing at a column that no longer exists would
        # render a header with nothing under it.
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        item = _add_act(program)
        program.fill_cell(item_id=item.id, column_id=column.id, value=CellValue("на стойке"), now=NOW)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Звукорежиссёр"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ColumnRef.of(ProgramColumn.TIME), column.ref],
        )

        program.remove_custom_column(column.id, now=NOW)
        assert program.custom_columns == ()
        assert program.item(item.id).value_in(column.id).is_blank
        assert [ref.key for ref in share.columns] == ["TIME"]

    def test_a_custom_column_can_be_published_like_any_other(self) -> None:
        program = _program()
        column = program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle("Микрофон"), now=NOW)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Звукорежиссёр"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[column.ref, ColumnRef.of(ProgramColumn.TIME)],
        )
        # Built-ins first in their own order, then the programme's own columns.
        assert [ref.key for ref in share.columns] == ["TIME", column.ref.key]

    def test_publishing_a_column_from_another_programme_is_refused(self) -> None:
        program = _program()
        with pytest.raises(ProgramColumnNotFoundError):
            program.add_share(
                share_id=uuid.uuid4(),
                name=ShareName("Чужое"),
                slug=PublicSlug("Foreign234"),
                now=NOW,
                columns=[ColumnRef.custom(uuid.uuid4())],
            )

    def test_a_column_reference_round_trips_through_its_wire_key(self) -> None:
        column_id = uuid.uuid4()
        assert ColumnRef.parse(f"custom:{column_id}") == ColumnRef.custom(column_id)
        assert ColumnRef.parse("time") == ColumnRef.of(ProgramColumn.TIME)
        with pytest.raises(InvalidProgramDataError):
            ColumnRef.parse("custom:not-a-uuid")


class TestTheDayItself:
    """What the host drives from their link while the festival is running."""

    def test_slots_start_pending(self) -> None:
        program = _program()
        assert _add_act(program).progress is ProgramItemProgress.PENDING
        assert program.on_stage is None

    def test_putting_an_act_on_stage_finishes_the_previous_one(self) -> None:
        # An act ends when the next one begins; a host should not have to say so twice.
        program = _program()
        first, second = _add_act(program), _add_act(program)
        program.set_item_progress(first.id, ProgramItemProgress.ON_STAGE, now=NOW)
        program.set_item_progress(second.id, ProgramItemProgress.ON_STAGE, now=NOW)

        assert program.item(first.id).progress is ProgramItemProgress.PERFORMED
        assert program.item(second.id).progress is ProgramItemProgress.ON_STAGE
        assert program.on_stage is not None
        assert program.on_stage.id == second.id

    def test_at_most_one_act_is_ever_on_stage(self) -> None:
        program = _program()
        items = [_add_act(program) for _ in range(3)]
        for item in items:
            program.set_item_progress(item.id, ProgramItemProgress.ON_STAGE, now=NOW)

        assert len([item for item in program.items if item.progress is ProgramItemProgress.ON_STAGE]) == 1

    def test_an_act_can_be_marked_performed_or_skipped_directly(self) -> None:
        program = _program()
        first, second = _add_act(program), _add_act(program)
        program.set_item_progress(first.id, ProgramItemProgress.PERFORMED, now=NOW)
        program.set_item_progress(second.id, ProgramItemProgress.SKIPPED, now=NOW)

        assert program.item(first.id).progress.is_finished
        assert program.item(second.id).progress.is_finished
        assert program.on_stage is None

    def test_progress_can_be_reset_for_a_rehearsal(self) -> None:
        program = _program()
        item = _add_act(program)
        program.set_item_progress(item.id, ProgramItemProgress.PERFORMED, now=NOW)

        program.reset_progress(now=NOW)
        assert program.item(item.id).progress is ProgramItemProgress.PENDING

    def test_a_link_controls_the_running_order_only_when_granted(self) -> None:
        program = _program()
        _add_act(program)
        screen = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        host = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Ведущий"),
            slug=PublicSlug("Host23456"),
            now=NOW,
            controls_running_order=True,
        )

        assert screen.controls_running_order is False
        assert host.controls_running_order is True

    def test_control_can_be_granted_and_withdrawn_later(self) -> None:
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Ведущий"), slug=PublicSlug("Host23456"), now=NOW)
        program.set_share_control(share.id, allowed=True, now=NOW)
        assert program.share(share.id).controls_running_order is True

        program.set_share_control(share.id, allowed=False, now=NOW)
        assert program.share(share.id).controls_running_order is False


class TestSlug:
    def test_a_generated_slug_is_valid_and_random(self) -> None:
        assert PublicSlug.generate() != PublicSlug.generate()

    def test_confusable_characters_are_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            PublicSlug("O0Il1-abc")

    def test_a_too_short_slug_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            PublicSlug("abc")
