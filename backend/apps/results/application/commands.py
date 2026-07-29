"""Command DTOs for the Results use cases.

Framework-neutral input shapes: primitives only, so a DRF view, a management command
or a test constructs them the same way. ``None`` consistently means "leave this as it
is" on the update commands, which is what lets one endpoint carry a partial edit
without a sentinel type.

The exception is :class:`AwardRowsCommand`, where ``None`` inside a pair means the
opposite - "clear this result". Clearing an award is an edit a jury makes, so the
absence of a value has to be expressible rather than indistinguishable from silence;
that is why the awards arrive as an explicit list of pairs and not as a partial map.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "AddRowCommand",
    "AwardRowsCommand",
    "CreateProtocolCommand",
    "PublishProtocolCommand",
    "ReorderRowsCommand",
    "UpdateProtocolCommand",
]


@dataclass(frozen=True, slots=True)
class CreateProtocolCommand:
    """Start a protocol for one nomination.

    ``seed`` is the normal path: the rows are copied from the nomination's programme, in
    running order and with its numbers, so the jury's table opens in the order the day
    ran. Without a programme it falls back to the nomination's competing acts; pass
    ``seed=False`` for a protocol assembled entirely by hand.
    """

    competition_id: str
    nomination_id: str
    name: str | None = None
    columns: tuple[str, ...] = ()
    seed: bool = True


@dataclass(frozen=True, slots=True)
class UpdateProtocolCommand:
    """Rename a protocol and/or change which columns its public page shows."""

    protocol_id: str
    name: str | None = None
    #: ``None`` leaves the selection alone; an empty tuple resets it to the safe default.
    columns: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class AddRowCommand:
    """Add one competing act to the protocol by hand.

    For the act that was slotted in on the day, or the one whose programme entry never
    existed. ``position`` inserts it where it actually performed rather than at the end.
    """

    protocol_id: str
    submission_id: str
    position: int | None = None
    award: str | None = None


@dataclass(frozen=True, slots=True)
class ReorderRowsCommand:
    """Apply a new order to the protocol's rows, numbers travelling with them."""

    protocol_id: str
    row_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AwardRowsCommand:
    """Write one or more results.

    Carries pairs rather than a map so ``(row, None)`` unambiguously means "clear this
    one" - a jury correcting itself needs that as much as it needs to set a value. One
    command covers both the single edit a dropdown makes and the batch a jury saves
    after working down a nomination.
    """

    protocol_id: str
    awards: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PublishProtocolCommand:
    """Publish the current results as a new revision.

    ``columns`` is accepted here as well as on the update command because choosing what
    the public page shows is part of the publish dialog: an organizer decides "показать
    педагога" in the same breath as pressing the button, and requiring two requests
    would let the page go out cut the wrong way.

    ``notify`` sends the letters. Default on - the letter is the point of publishing -
    but a re-publication that only fixes a column selection has nothing to announce, and
    thirty studios do not need a second letter to find that out.
    """

    protocol_id: str
    columns: tuple[str, ...] | None = None
    notify: bool = True
