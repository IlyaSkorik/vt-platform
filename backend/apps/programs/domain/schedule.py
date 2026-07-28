"""Turning a running order into a timetable - the Programs context's core rule.

One pure function over the aggregate's items, its buffer and its start time. It has
no dependencies on Django, on persistence or on any other context, which is what
makes "10:00 / 10:04 / 10:08" cheap to reason about and exhaustively testable.

Two rules decide everything:

* **A slot is as long as its item, plus the buffer when the kind takes one.** Today
  only a performance takes it, so ``3:20 + 0:30`` occupies ``3:50`` while the act
  itself is still ``3:20`` everywhere in the platform. A break is already slack and
  is used exactly as sized.
* **Every item starts where the previous one ended.** The program is a single
  sequence, so an offset is the running total of the slots before it. Wall-clock
  times appear on top of those offsets once the program has a start time; without
  one the shape of the day is still complete, it just has no clock yet.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from .entities import ProgramItem
from .value_objects import TimeBuffer

__all__ = ["ScheduledItem", "build_schedule", "total_duration_seconds"]


@dataclass(frozen=True, slots=True)
class ScheduledItem:
    """One item placed on the timeline.

    ``slot_seconds`` is the item's own length plus any buffer - the space it takes in
    the day. ``duration_seconds`` stays the item's own length, so a client can show
    both "номер 3:20" and "слот 3:50" without recomputing the rule.
    """

    item: ProgramItem
    position: int
    offset_seconds: int
    duration_seconds: int
    slot_seconds: int
    starts_at: datetime | None
    ends_at: datetime | None

    @property
    def buffer_seconds(self) -> int:
        """The padding this slot received (0 for kinds that take none)."""
        return self.slot_seconds - self.duration_seconds


def build_schedule(
    *,
    items: Sequence[ProgramItem],
    buffer: TimeBuffer,
    starts_at: datetime | None = None,
) -> tuple[ScheduledItem, ...]:
    """Place every item on the timeline, in order.

    ``position`` is 1-based because it is what the organizer and every printed
    program count with ("пункты 25-40").
    """
    scheduled: list[ScheduledItem] = []
    offset = 0
    for index, item in enumerate(items, start=1):
        duration = item.duration.seconds
        slot = duration + (buffer.seconds if item.kind.takes_buffer else 0)
        item_starts_at = starts_at + timedelta(seconds=offset) if starts_at is not None else None
        # An item *ends* when the item itself ends, not when its padded slot does:
        # the buffer is the gap before the next one, not part of this performance.
        scheduled.append(
            ScheduledItem(
                item=item,
                position=index,
                offset_seconds=offset,
                duration_seconds=duration,
                slot_seconds=slot,
                starts_at=item_starts_at,
                ends_at=item_starts_at + timedelta(seconds=duration) if item_starts_at is not None else None,
            )
        )
        offset += slot
    return tuple(scheduled)


def total_duration_seconds(*, items: Sequence[ProgramItem], buffer: TimeBuffer) -> int:
    """How long the whole program runs, buffers included."""
    return sum(item.duration.seconds + (buffer.seconds if item.kind.takes_buffer else 0) for item in items)
