"""Unit tests for the Programs schedule calculation.

The whole point of the module: a running order plus a buffer plus a start time turns
into "10:00 / 10:04 / 10:08". Pure functions over the aggregate, so no database and no
clock are involved.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.programs.domain.entities import ProgramItem
from apps.programs.domain.schedule import build_schedule, total_duration_seconds
from apps.programs.domain.value_objects import (
    ItemDuration,
    ItemTitle,
    ProgramItemKind,
    TimeBuffer,
)

TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


def _act(seconds: int) -> ProgramItem:
    return ProgramItem.performance(item_id=uuid.uuid4(), submission_id=uuid.uuid4(), duration=ItemDuration(seconds))


def _break(seconds: int, title: str = "Перерыв") -> ProgramItem:
    return ProgramItem.block(
        item_id=uuid.uuid4(),
        kind=ProgramItemKind.BREAK,
        title=ItemTitle(title),
        duration=ItemDuration(seconds),
    )


class TestWallClockTimes:
    def test_each_item_starts_where_the_previous_slot_ended(self) -> None:
        schedule = build_schedule(
            items=[_act(200), _act(200), _act(200)],
            buffer=TimeBuffer(seconds=40),
            starts_at=TEN_AM,
        )
        assert [entry.starts_at for entry in schedule] == [
            datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 1, 10, 4, tzinfo=UTC),
            datetime(2026, 8, 1, 10, 8, tzinfo=UTC),
        ]

    def test_positions_are_one_based(self) -> None:
        # "Пункты 25-40" is how an organizer talks about a program, so the numbering
        # a client renders must be the numbering the domain produced.
        schedule = build_schedule(items=[_act(60), _break(300), _act(60)], buffer=TimeBuffer.none(), starts_at=None)
        assert [entry.position for entry in schedule] == [1, 2, 3]

    def test_without_a_start_time_the_shape_is_still_complete(self) -> None:
        schedule = build_schedule(items=[_act(200), _act(100)], buffer=TimeBuffer(seconds=30), starts_at=None)
        assert [entry.offset_seconds for entry in schedule] == [0, 230]
        assert all(entry.starts_at is None and entry.ends_at is None for entry in schedule)

    def test_an_item_ends_when_the_act_ends_not_when_its_padded_slot_does(self) -> None:
        schedule = build_schedule(items=[_act(200)], buffer=TimeBuffer(seconds=30), starts_at=TEN_AM)
        assert schedule[0].ends_at == datetime(2026, 8, 1, 10, 3, 20, tzinfo=UTC)

    def test_an_empty_program_schedules_to_nothing(self) -> None:
        assert build_schedule(items=[], buffer=TimeBuffer(seconds=30), starts_at=TEN_AM) == ()


class TestBuffer:
    def test_a_performance_slot_is_the_act_plus_the_buffer(self) -> None:
        # 3:20 + 0:30 = 3:50, and the act is still 3:20.
        schedule = build_schedule(items=[_act(200)], buffer=TimeBuffer(seconds=30), starts_at=None)
        assert schedule[0].duration_seconds == 200
        assert schedule[0].slot_seconds == 230
        assert schedule[0].buffer_seconds == 30

    def test_a_break_is_used_exactly_as_sized(self) -> None:
        # A break is already slack; padding it would stretch what the organizer sized.
        schedule = build_schedule(items=[_break(900)], buffer=TimeBuffer(seconds=45), starts_at=None)
        assert schedule[0].slot_seconds == 900
        assert schedule[0].buffer_seconds == 0

    def test_raising_the_buffer_shifts_everything_after_the_first_act(self) -> None:
        items = [_act(180), _act(180)]
        tight = build_schedule(items=items, buffer=TimeBuffer.none(), starts_at=TEN_AM)
        padded = build_schedule(items=items, buffer=TimeBuffer(seconds=60), starts_at=TEN_AM)
        assert tight[1].starts_at == datetime(2026, 8, 1, 10, 3, tzinfo=UTC)
        assert padded[1].starts_at == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)
        # The first item never moves - it starts when the program starts.
        assert tight[0].starts_at == padded[0].starts_at

    def test_no_buffer_at_all_is_a_valid_setting(self) -> None:
        schedule = build_schedule(items=[_act(120), _act(120)], buffer=TimeBuffer.none(), starts_at=None)
        assert [entry.offset_seconds for entry in schedule] == [0, 120]


class TestTotalDuration:
    def test_totals_count_buffers_but_not_break_padding(self) -> None:
        items = [_act(200), _break(600), _act(200)]
        assert total_duration_seconds(items=items, buffer=TimeBuffer(seconds=30)) == 200 + 30 + 600 + 200 + 30

    def test_an_empty_program_lasts_no_time(self) -> None:
        assert total_duration_seconds(items=[], buffer=TimeBuffer(seconds=30)) == 0


class TestMixedRunningOrder:
    def test_a_break_pushes_every_later_act(self) -> None:
        # The case the constructor exists for: dropping "Обед 40 минут" in the middle
        # must re-time the whole afternoon without touching a single act.
        first, second = _act(180), _act(180)
        lunch = _break(2400, "Обед")
        before = build_schedule(items=[first, second], buffer=TimeBuffer.none(), starts_at=TEN_AM)
        after = build_schedule(items=[first, lunch, second], buffer=TimeBuffer.none(), starts_at=TEN_AM)
        assert before[1].starts_at == datetime(2026, 8, 1, 10, 3, tzinfo=UTC)
        assert after[2].starts_at == datetime(2026, 8, 1, 10, 43, tzinfo=UTC)
        assert after[2].duration_seconds == 180
