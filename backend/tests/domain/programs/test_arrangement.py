"""Unit tests for generating a running order (VT-86).

The whole point of the module: a pile of competing acts plus a set of rules turns into
the sequence an organizer would otherwise have assembled by dragging rows. Pure values
throughout - no database, no clock, no other context - so a whole festival day can be
asserted on in a few lines.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from apps.programs.domain.arrangement import ArrangedItem, ArrangementCandidate, arrange
from apps.programs.domain.exceptions import InvalidProgramDataError
from apps.programs.domain.value_objects import (
    ArrangementBlock,
    ArrangementSettings,
    BreakRule,
    GroupingAxis,
    ItemDuration,
    ItemTitle,
    PerformanceOrder,
    ProgramItemKind,
    TimeBuffer,
)

NO_BUFFER = TimeBuffer.none()


def _act(
    title: str,
    *,
    seconds: int = 180,
    nomination: str | None = "Вокал",
    discipline: str | None = "Эстрадный вокал",
    age: str | None = None,
    age_order: int | None = None,
    group: str | None = None,
    organization: str | None = None,
    people: tuple[str, ...] = (),
) -> ArrangementCandidate:
    return ArrangementCandidate(
        submission_id=uuid.uuid4(),
        duration_seconds=seconds,
        title=title,
        nomination=nomination,
        discipline=discipline,
        age_category=age,
        age_order=age_order,
        participant_group=group,
        organization=organization,
        participants=people,
    )


def _titles(items: Sequence[ArrangedItem], acts: list[ArrangementCandidate]) -> list[str]:
    """Render a generated running order as the names a reader would see down the page."""
    by_id = {act.submission_id: act.title for act in acts}
    return [by_id[item.submission_id] if item.submission_id is not None else str(item.title) for item in items]


class TestGrouping:
    def test_acts_are_bucketed_along_the_chosen_axes_in_the_chosen_order(self) -> None:
        # Grouping by nomination then discipline must not interleave the disciplines of
        # one nomination with another's - that is the whole promise of "сгруппировать".
        acts = [
            _act("Б", nomination="Хореография", discipline="Народный танец"),
            _act("А", nomination="Вокал", discipline="Эстрадный вокал"),
            _act("В", nomination="Вокал", discipline="Академический вокал"),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(GroupingAxis.NOMINATION, GroupingAxis.DISCIPLINE)),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["В", "А", "Б"]

    def test_age_bands_are_ordered_as_ages_not_as_text(self) -> None:
        # "10-12 лет" sorts before "7-9 лет" alphabetically and after it as an age. The
        # band's own ordinal is what the generator reads, which is why it travels on the act.
        acts = [
            _act("старшие", age="10-12 лет", age_order=1),
            _act("младшие", age="7-9 лет", age_order=0),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(GroupingAxis.AGE_CATEGORY,)),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["младшие", "старшие"]

    def test_acts_with_nothing_on_an_axis_go_last(self) -> None:
        acts = [_act("без номинации", nomination=None), _act("с номинацией", nomination="Вокал")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(GroupingAxis.NOMINATION,)),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["с номинацией", "без номинации"]

    def test_no_axes_at_all_is_one_sequence(self) -> None:
        acts = [_act("Б"), _act("А")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Б"]

    def test_an_empty_catalog_produces_an_empty_programme(self) -> None:
        # Not a day consisting of an opening and an award with nothing between them.
        items = arrange(
            candidates=[],
            settings=ArrangementSettings(
                opens_with=ArrangementBlock.of("Открытие", seconds=600),
                closes_with=ArrangementBlock.of("Награждение", seconds=900),
            ),
            buffer=NO_BUFFER,
        )
        assert items == ()


class TestOrderWithinGroup:
    def test_youngest_first_is_the_default_reading_of_a_group(self) -> None:
        acts = [_act("старший", age_order=5), _act("младший", age_order=1)]
        items = arrange(candidates=acts, settings=ArrangementSettings(grouping=()), buffer=NO_BUFFER)
        assert _titles(items, acts) == ["младший", "старший"]

    @pytest.mark.parametrize(
        ("order", "expected"),
        [
            (PerformanceOrder.AGE_DESC, ["старший", "младший"]),
            (PerformanceOrder.DURATION_ASC, ["младший", "старший"]),
            (PerformanceOrder.DURATION_DESC, ["старший", "младший"]),
        ],
    )
    def test_each_order_is_honoured(self, order: PerformanceOrder, expected: list[str]) -> None:
        acts = [_act("старший", seconds=300, age_order=5), _act("младший", seconds=100, age_order=1)]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=order),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == expected

    def test_acts_with_no_organization_sort_after_those_that_have_one(self) -> None:
        acts = [_act("ничей"), _act("школьный", organization="Школа №1")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.ORGANIZATION),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["школьный", "ничей"]

    def test_a_tie_is_broken_the_same_way_on_every_rebuild(self) -> None:
        # A programme that reshuffles its ties each time it is regenerated is one nobody
        # can proofread against the copy they printed yesterday.
        acts = [_act("Б", seconds=180), _act("А", seconds=180), _act("В", seconds=180)]
        settings = ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.DURATION_ASC)
        first = arrange(candidates=acts, settings=settings, buffer=NO_BUFFER)
        again = arrange(candidates=list(reversed(acts)), settings=settings, buffer=NO_BUFFER)
        assert _titles(first, acts) == _titles(again, acts) == ["А", "Б", "В"]


class TestSpacingRepeats:
    def test_a_participant_does_not_perform_twice_in_a_row(self) -> None:
        acts = [
            _act("А", people=("Иванова Мария",)),
            _act("Б", people=("Иванова Мария",)),
            _act("В", people=("Петров Пётр",)),
            _act("Г", people=("Сидоров Иван",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE, repeat_gap=2),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "В", "Г", "Б"]

    def test_the_names_are_compared_regardless_of_case(self) -> None:
        acts = [
            _act("А", people=("Иванова Мария",)),
            _act("Б", people=("ИВАНОВА МАРИЯ",)),
            _act("В", people=("Петров Пётр",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE, repeat_gap=1),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "В", "Б"]

    def test_a_duet_counts_for_both_of_its_participants(self) -> None:
        acts = [
            _act("дуэт", people=("Иванова Мария", "Петров Пётр")),
            _act("соло Петрова", people=("Петров Пётр",)),
            _act("чужое", people=("Сидоров Иван",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE, repeat_gap=1),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["дуэт", "чужое", "соло Петрова"]

    def test_spacing_never_moves_an_act_out_of_its_group(self) -> None:
        # The organizer's first instruction outranks the second: a gap that could only be
        # honoured by breaking the grouping is simply not honoured.
        acts = [
            _act("вокал 1", nomination="Вокал", people=("Иванова Мария",)),
            _act("вокал 2", nomination="Вокал", people=("Иванова Мария",)),
            _act("танец", nomination="Хореография", people=("Петров Пётр",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(GroupingAxis.NOMINATION,),
                order_within_group=PerformanceOrder.TITLE,
                repeat_gap=3,
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["вокал 1", "вокал 2", "танец"]

    def test_an_unhonourable_gap_is_still_made_as_wide_as_the_group_allows(self) -> None:
        # A trio with two numbers in a group of four: the gap asked for is wider than
        # the group, so it cannot be honoured at all. The programme is still built —
        # and the two numbers end up as far apart as four slots permit, rather than
        # the generator shrugging and taking whatever came first.
        pair = ("Иванова Мария", "Петров Пётр", "Сидоров Иван")
        acts = [
            _act("А", people=pair),
            _act("Б", people=("Кузнецова Анна",)),
            _act("В", people=pair),
            _act("Г", people=("Орлов Артём",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE, repeat_gap=5),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Б", "Г", "В"]

    def test_an_impossible_gap_still_produces_a_programme(self) -> None:
        # A soloist with three of the four numbers cannot be spaced out. Refusing to
        # generate anything would be worse than a tight change.
        acts = [_act(name, people=("Иванова Мария",)) for name in ("А", "Б", "В")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), order_within_group=PerformanceOrder.TITLE, repeat_gap=5),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Б", "В"]

    def test_the_gap_also_holds_across_a_group_boundary_when_there_is_slack(self) -> None:
        acts = [
            _act("вокал", nomination="Вокал", people=("Иванова Мария",)),
            _act("танец соло", nomination="Хореография", people=("Иванова Мария",)),
            _act("танец пара", nomination="Хореография", people=("Петров Пётр",)),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(GroupingAxis.NOMINATION,),
                order_within_group=PerformanceOrder.TITLE,
                repeat_gap=1,
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["вокал", "танец пара", "танец соло"]


class TestBreaks:
    def test_a_break_lands_wherever_the_top_group_changes(self) -> None:
        acts = [
            _act("вокал 1", nomination="Вокал"),
            _act("вокал 2", nomination="Вокал"),
            _act("танец", nomination="Хореография"),
        ]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(GroupingAxis.NOMINATION,),
                order_within_group=PerformanceOrder.TITLE,
                break_rule=BreakRule.BETWEEN_GROUPS,
                break_block=ArrangementBlock.of("Перерыв", seconds=600),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["вокал 1", "вокал 2", "Перерыв", "танец"]

    def test_a_break_every_n_acts(self) -> None:
        acts = [_act(name) for name in ("А", "Б", "В", "Г", "Д")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                order_within_group=PerformanceOrder.TITLE,
                break_rule=BreakRule.EVERY_COUNT,
                break_after_items=2,
                break_block=ArrangementBlock.of("Перерыв", seconds=600),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Б", "Перерыв", "В", "Г", "Перерыв", "Д"]

    def test_a_break_closes_an_otdelenie_that_would_otherwise_overrun(self) -> None:
        # Measured on the slot about to be placed, so an отделение never crosses its
        # limit - it stops just short of it.
        acts = [_act(name, seconds=600) for name in ("А", "Б", "В")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                order_within_group=PerformanceOrder.TITLE,
                break_rule=BreakRule.EVERY_DURATION,
                break_after_seconds=1500,
                break_block=ArrangementBlock.of("Антракт", seconds=900),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Б", "Антракт", "В"]

    def test_the_buffer_counts_towards_the_otdelenie(self) -> None:
        # A day runs with its buffer in it, so a rule measured in minutes has to count
        # the day as it will actually run: 2 x (600 + 300) already passes 1500.
        acts = [_act(name, seconds=600) for name in ("А", "Б", "В")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                order_within_group=PerformanceOrder.TITLE,
                break_rule=BreakRule.EVERY_DURATION,
                break_after_seconds=1500,
                break_block=ArrangementBlock.of("Антракт", seconds=900),
            ),
            buffer=TimeBuffer(seconds=300),
        )
        assert _titles(items, acts) == ["А", "Антракт", "Б", "Антракт", "В"]

    def test_an_act_longer_than_the_limit_simply_overruns(self) -> None:
        acts = [_act("длинный", seconds=3600)]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                break_rule=BreakRule.EVERY_DURATION,
                break_after_seconds=600,
                break_block=ArrangementBlock.of("Перерыв", seconds=600),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["длинный"]

    def test_a_programme_never_opens_or_closes_on_a_break(self) -> None:
        acts = [_act("А"), _act("Б")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                order_within_group=PerformanceOrder.TITLE,
                break_rule=BreakRule.EVERY_COUNT,
                break_after_items=1,
                break_block=ArrangementBlock.of("Перерыв", seconds=600),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["А", "Перерыв", "Б"]


class TestServiceBlocks:
    def test_an_opening_and_an_award_wrap_the_day(self) -> None:
        acts = [_act("А"), _act("Б")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(
                grouping=(),
                order_within_group=PerformanceOrder.TITLE,
                opens_with=ArrangementBlock.of("Открытие", seconds=600),
                closes_with=ArrangementBlock.of("Награждение", seconds=1800),
            ),
            buffer=NO_BUFFER,
        )
        assert _titles(items, acts) == ["Открытие", "А", "Б", "Награждение"]
        assert [item.kind for item in items] == [
            ProgramItemKind.OPENING,
            ProgramItemKind.PERFORMANCE,
            ProgramItemKind.PERFORMANCE,
            ProgramItemKind.AWARD,
        ]

    def test_a_performance_slot_is_as_long_as_its_act(self) -> None:
        acts = [_act("А", seconds=215)]
        items = arrange(candidates=acts, settings=ArrangementSettings(grouping=()), buffer=TimeBuffer(seconds=30))
        assert items[0].duration == ItemDuration(215)
        assert items[0].title is None

    def test_a_generated_block_carries_its_own_title(self) -> None:
        acts = [_act("А")]
        items = arrange(
            candidates=acts,
            settings=ArrangementSettings(grouping=(), opens_with=ArrangementBlock.of("Открытие", seconds=600)),
            buffer=NO_BUFFER,
        )
        assert items[0].title == ItemTitle("Открытие")
        assert items[0].submission_id is None


class TestSettingsValidation:
    def test_a_break_rule_without_a_break_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ArrangementSettings(break_rule=BreakRule.EVERY_COUNT, break_after_items=5)

    def test_an_interval_of_zero_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ArrangementSettings(
                break_rule=BreakRule.EVERY_DURATION,
                break_after_seconds=0,
                break_block=ArrangementBlock.of("Перерыв", seconds=600),
            )

    def test_the_same_axis_cannot_be_chosen_twice(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ArrangementSettings(grouping=(GroupingAxis.NOMINATION, GroupingAxis.NOMINATION))

    def test_a_negative_gap_is_refused(self) -> None:
        with pytest.raises(InvalidProgramDataError):
            ArrangementSettings(repeat_gap=-1)
