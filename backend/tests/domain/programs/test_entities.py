"""Unit tests for the ``Program`` aggregate and its value objects.

Covers what the aggregate refuses as much as what it allows: the running order is the
thing the whole day is run from, so an act cannot be doubled, a reorder cannot lose a
slot, and a public edition cannot point at something that is not in the program.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.programs.domain.entities import Program, ProgramItem
from apps.programs.domain.exceptions import (
    InvalidProgramDataError,
    ItemNotInProgramError,
    PerformanceAlreadyInProgramError,
    ProgramItemNotFoundError,
    ProgramShareNotFoundError,
    ReorderMismatchError,
)
from apps.programs.domain.value_objects import (
    COLUMN_LABELS,
    DEFAULT_PUBLIC_COLUMNS,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
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
            Program(  # type: ignore[call-arg]
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
        assert share.columns == DEFAULT_PUBLIC_COLUMNS

    def test_columns_are_kept_in_canonical_order(self) -> None:
        program = _program()
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Звукорежиссёр"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ProgramColumn.COMMENT, ProgramColumn.TITLE, ProgramColumn.TIME],
        )
        assert share.columns == (ProgramColumn.TIME, ProgramColumn.TITLE, ProgramColumn.COMMENT)

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
        assert program.share(share.id).columns == (ProgramColumn.TIME, ProgramColumn.PARTICIPANT)
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
        assert ProgramColumn.COMMENT in engineer.columns
        assert ProgramColumn.COMMENT not in screen.columns

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


class TestSlug:
    def test_a_generated_slug_is_valid_and_random(self) -> None:
        assert PublicSlug.generate() != PublicSlug.generate()

    def test_confusable_characters_are_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            PublicSlug("O0Il1-abc")

    def test_a_too_short_slug_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            PublicSlug("abc")
