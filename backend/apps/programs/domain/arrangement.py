"""Turning a set of competing acts into a running order - the other half of a programme.

:mod:`apps.programs.domain.schedule` answers "when does item 17 go on stage"; this
module answers the question before it: **which acts, in which order, with what between
them**. Together they are the whole of what a programme is, and both are pure functions
over values - no Django, no repository, no clock - so a festival day can be rehearsed in
a unit test.

The algorithm is deliberately a sequence of three understandable passes rather than one
clever optimiser, because the organizer has to be able to look at the result and see
their own settings in it:

1. **Group.** Acts are bucketed along the chosen axes, in the order those axes were
   chosen, and the buckets are laid out in a meaningful order - age bands by actual age
   rather than by the spelling of their names, everything else alphabetically, and
   "не указано" last.
2. **Order, then space out.** Inside a bucket acts take the chosen order; then, if the
   organizer asked for it, an act is deferred when one of its participants is still
   catching their breath from an earlier slot. The deferral only ever swaps acts *within
   one bucket*, so spacing can never silently undo the grouping - the organizer's first
   instruction outranks the second.
3. **Insert service blocks.** Breaks go where the chosen rule fires, never first and
   never last, and an opening or an award wraps the day.

What the generator does *not* do is decide which acts take part - that is the catalog's
rule (see ``DjangoPerformanceCatalog``) - and it does not number anything, because
numbers belong to the aggregate that issues them.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from .value_objects import (
    ArrangementSettings,
    BreakRule,
    GroupingAxis,
    ItemDuration,
    ItemTitle,
    PerformanceOrder,
    ProgramItemKind,
    TimeBuffer,
)

__all__ = ["ArrangedItem", "ArrangementCandidate", "arrange"]

#: Where an act with no value on a grouping axis is placed: after everything that has
#: one. "Возраст не указан" at the top of the programme would read as a mistake.
_LAST: Final[tuple[int, int, str]] = (1, 0, "")

#: The ordinal an age band with no ``sort_order`` of its own takes: after every band
#: that has one, where it then sorts by name among its fellows.
_UNRANKED_AGE: Final = 1_000_000


@dataclass(frozen=True, slots=True)
class ArrangementCandidate:
    """One act as the generator needs to see it.

    A flat value, not a reference into another context: everything the rules read -
    the facets to group by, the age band to sort by, the people to space apart - is
    already resolved here, which is what keeps this module free of every dependency.
    """

    submission_id: uuid.UUID
    duration_seconds: int
    title: str = ""
    nomination: str | None = None
    discipline: str | None = None
    age_category: str | None = None
    #: Where this age band sits among the others. Names like "7-9 лет" and "10-12 лет"
    #: do not sort as ages, so the band's own ordinal travels with the act.
    age_order: int | None = None
    participant_group: str | None = None
    participation_format: str | None = None
    organization: str | None = None
    participants: tuple[str, ...] = ()

    def facet(self, axis: GroupingAxis) -> str | None:
        """This act's value on one grouping axis."""
        return {
            GroupingAxis.NOMINATION: self.nomination,
            GroupingAxis.DISCIPLINE: self.discipline,
            GroupingAxis.AGE_CATEGORY: self.age_category,
            GroupingAxis.PARTICIPANT_GROUP: self.participant_group,
            GroupingAxis.PARTICIPATION_FORMAT: self.participation_format,
            GroupingAxis.ORGANIZATION: self.organization,
        }[axis]

    @property
    def people(self) -> frozenset[str]:
        """The participants of this act, normalised for comparison."""
        return frozenset(name.casefold() for name in self.participants if name.strip())


@dataclass(frozen=True, slots=True)
class ArrangedItem:
    """One slot of the generated running order, ready for the aggregate to create.

    The same two shapes :class:`~apps.programs.domain.entities.ProgramItem` has: an act
    bound to a submission, or a standalone block carrying its own title.
    """

    kind: ProgramItemKind
    duration: ItemDuration
    submission_id: uuid.UUID | None = None
    title: ItemTitle | None = None

    @classmethod
    def performance(cls, candidate: ArrangementCandidate) -> ArrangedItem:
        """A slot for one act, as long as the act itself."""
        return cls(
            kind=ProgramItemKind.PERFORMANCE,
            duration=ItemDuration(candidate.duration_seconds),
            submission_id=candidate.submission_id,
        )

    @classmethod
    def block(cls, *, kind: ProgramItemKind, title: ItemTitle, duration: ItemDuration) -> ArrangedItem:
        """A service slot - a break, an opening, an award."""
        return cls(kind=kind, duration=duration, title=title)


@dataclass(slots=True)
class _Bucket:
    """One group of acts, with the sort key that decides where the group itself goes."""

    key: tuple[tuple[int, int, str], ...]
    #: The value of the *first* grouping axis, which is what a between-groups break cuts along.
    top: str | None
    acts: list[ArrangementCandidate] = field(default_factory=list)


def arrange(
    *,
    candidates: Sequence[ArrangementCandidate],
    settings: ArrangementSettings,
    buffer: TimeBuffer,
) -> tuple[ArrangedItem, ...]:
    """Build a complete running order out of ``candidates``.

    ``buffer`` is the programme's own padding: a break rule measured in minutes has to
    count the day as it will actually run, and a day runs with the buffer in it.

    An empty catalog produces an empty programme - not a day consisting of an opening
    and an award with nothing between them.
    """
    if not candidates:
        return ()
    buckets = _bucket(candidates, settings.grouping)
    ordered = _space_out(buckets, settings)
    return _with_blocks(ordered, settings=settings, buffer=buffer)


# ----------------------------------------------------------------------
# 1. Grouping
# ----------------------------------------------------------------------


def _bucket(candidates: Sequence[ArrangementCandidate], grouping: Sequence[GroupingAxis]) -> list[_Bucket]:
    """Split the acts into groups and put the groups in order.

    With no axes chosen the whole catalog is a single group, which is the honest
    reading of "не группировать": one sequence, ordered and spaced like any other.
    """
    if not grouping:
        return [_Bucket(key=(), top=None, acts=list(candidates))]
    buckets: dict[tuple[str | None, ...], _Bucket] = {}
    for candidate in candidates:
        identity = tuple(candidate.facet(axis) for axis in grouping)
        bucket = buckets.get(identity)
        if bucket is None:
            bucket = _Bucket(
                key=tuple(_axis_key(candidate, axis) for axis in grouping),
                top=identity[0],
            )
            buckets[identity] = bucket
        bucket.acts.append(candidate)
    return sorted(buckets.values(), key=lambda bucket: bucket.key)


def _axis_key(candidate: ArrangementCandidate, axis: GroupingAxis) -> tuple[int, int, str]:
    """How one group sorts against another on one axis.

    A fixed ``(missing, ordinal, text)`` triple rather than "a number for ages and a
    string for the rest": two groups on the same axis have to stay comparable even when
    only one of them carries an ordinal, which a union-typed key is not.

    The leading flag is "has no value", so unclassified acts sink to the bottom of every
    axis at once instead of sorting in under an empty string.
    """
    value = candidate.facet(axis)
    if value is None or not value.strip():
        return _LAST
    if axis is GroupingAxis.AGE_CATEGORY:
        # Age bands are read as ages, never as text: "7-9 лет" comes before "10-12 лет".
        # A band with no ordinal of its own falls back to its name, after the numbered ones.
        ordinal = candidate.age_order
        return (0, ordinal, "") if ordinal is not None else (0, _UNRANKED_AGE, value.casefold())
    return (0, 0, value.casefold())


# ----------------------------------------------------------------------
# 2. Ordering inside a group, and spacing a participant's own acts apart
# ----------------------------------------------------------------------


def _space_out(buckets: Sequence[_Bucket], settings: ArrangementSettings) -> list[tuple[ArrangementCandidate, str | None]]:
    """Flatten the groups into one sequence, each act tagged with its top-axis value.

    Ordering happens per group; the spacing pass then walks the groups in order with a
    single memory of who has already been on stage, so the gap also holds across a group
    boundary whenever the next group has the slack to honour it.
    """
    emitted: list[tuple[ArrangementCandidate, str | None]] = []
    last_seen: dict[str, int] = {}
    for bucket in buckets:
        pool = sorted(bucket.acts, key=lambda act: _within_group_key(act, settings.order_within_group))
        while pool:
            index = _next_act(pool, last_seen=last_seen, position=len(emitted), gap=settings.repeat_gap)
            act = pool.pop(index)
            for person in act.people:
                last_seen[person] = len(emitted)
            emitted.append((act, bucket.top))
    return emitted


def _within_group_key(act: ArrangementCandidate, order: PerformanceOrder) -> tuple[object, ...]:
    """The sort key one act takes inside its group.

    Every key ends with the act's title and its id, so two acts that tie on the chosen
    criterion still come out in the same order on every regeneration - a programme that
    reshuffles its ties each time it is rebuilt is one nobody can proofread.
    """
    tail = (act.title.casefold(), str(act.submission_id))
    age = act.age_order if act.age_order is not None else 1_000_000
    match order:
        case PerformanceOrder.AGE_ASC:
            return (age, *tail)
        case PerformanceOrder.AGE_DESC:
            return (-age, *tail)
        case PerformanceOrder.DURATION_ASC:
            return (act.duration_seconds, *tail)
        case PerformanceOrder.DURATION_DESC:
            return (-act.duration_seconds, *tail)
        case PerformanceOrder.PARTICIPANT:
            lead = act.participants[0].casefold() if act.participants else ""
            return ((1, "") if not lead else (0, lead), *tail)
        case PerformanceOrder.ORGANIZATION:
            org = (act.organization or "").casefold()
            return ((1, "") if not org else (0, org), *tail)
        case PerformanceOrder.TITLE:
            return tail
    raise AssertionError(f"Unhandled performance order {order!r}")


def _next_act(pool: Sequence[ArrangementCandidate], *, last_seen: dict[str, int], position: int, gap: int) -> int:
    """Index of the act that should go on stage next, out of what this group has left.

    The first act whose participants have all had ``gap`` slots since their last one.

    When nobody qualifies - a trio with two numbers in a group of four, where the gap
    asked for is simply wider than the group - the programme is still built: the
    constraint is a preference about comfort, and refusing to generate a day over it
    would be worse than a tight change. But "still built" is not "built carelessly":
    the act that goes on is the one whose people have been off stage longest, so an
    interval that cannot be honoured is at least made as wide as this group allows.
    Ties keep the chosen order, which is what keeps a rebuild reproducible.
    """
    if gap <= 0:
        return 0
    best_index, best_wait = 0, -1
    for index, act in enumerate(pool):
        # How recently anyone in this act was last on stage; absent means never.
        latest = max((last_seen[person] for person in act.people if person in last_seen), default=None)
        if latest is None or position - latest > gap:
            return index
        if position - latest > best_wait:
            best_index, best_wait = index, position - latest
    return best_index


# ----------------------------------------------------------------------
# 3. Service blocks
# ----------------------------------------------------------------------


def _with_blocks(
    ordered: Sequence[tuple[ArrangementCandidate, str | None]],
    *,
    settings: ArrangementSettings,
    buffer: TimeBuffer,
) -> tuple[ArrangedItem, ...]:
    """Lay the acts out and drop the service blocks in between them.

    A break is only ever *between* acts: the rule is checked before an act is placed and
    only once something already stands before it, so a programme can neither open on a
    break nor end on one, whatever the settings say.
    """
    items: list[ArrangedItem] = []
    if settings.opens_with is not None:
        items.append(
            ArrangedItem.block(
                kind=ProgramItemKind.OPENING,
                title=settings.opens_with.title,
                duration=settings.opens_with.duration,
            )
        )
    # A rule and its block are inseparable - ``ArrangementSettings`` refuses one without
    # the other - so reading them together once is what lets the loop below stay a loop
    # about breaks rather than one about whether a break is possible.
    pause = settings.break_block if settings.break_rule is not BreakRule.NONE else None
    seconds_since_break = 0
    acts_since_break = 0
    previous_top: str | None = None
    first = True
    for candidate, top in ordered:
        slot = candidate.duration_seconds + buffer.seconds
        if (
            pause is not None
            and not first
            and _break_due(
                settings=settings,
                acts_since_break=acts_since_break,
                seconds_since_break=seconds_since_break,
                next_slot=slot,
                top=top,
                previous_top=previous_top,
            )
        ):
            items.append(ArrangedItem.block(kind=ProgramItemKind.BREAK, title=pause.title, duration=pause.duration))
            seconds_since_break = 0
            acts_since_break = 0
        items.append(ArrangedItem.performance(candidate))
        seconds_since_break += slot
        acts_since_break += 1
        previous_top = top
        first = False
    if settings.closes_with is not None:
        items.append(
            ArrangedItem.block(
                kind=ProgramItemKind.AWARD,
                title=settings.closes_with.title,
                duration=settings.closes_with.duration,
            )
        )
    return tuple(items)


def _break_due(
    *,
    settings: ArrangementSettings,
    acts_since_break: int,
    seconds_since_break: int,
    next_slot: int,
    top: str | None,
    previous_top: str | None,
) -> bool:
    """Whether a break belongs immediately before the next act."""
    if acts_since_break == 0:
        # Two breaks in a row, or a break before the first act of a section: never.
        return False
    match settings.break_rule:
        case BreakRule.NONE:
            return False
        case BreakRule.BETWEEN_GROUPS:
            return top != previous_top
        case BreakRule.EVERY_COUNT:
            return acts_since_break >= settings.break_after_items
        case BreakRule.EVERY_DURATION:
            # Checked against the slot about to be placed, so an отделение overruns its
            # limit only when a single act is longer than the limit itself.
            return seconds_since_break + next_slot > settings.break_after_seconds
    raise AssertionError(f"Unhandled break rule {settings.break_rule!r}")
