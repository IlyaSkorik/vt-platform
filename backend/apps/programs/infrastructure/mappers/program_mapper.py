"""Translation between the :class:`Program` aggregate and its four tables.

The only place that knows both shapes (ARCH-001 §7.2). Order is the one thing worth
watching: the aggregate's item *list* is authoritative, so writing enumerates it and
reading sorts by the recorded ``position`` - a row's ordinal is a projection of the
list, never an input to it.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.programs.domain.entities import CustomColumn, Program, ProgramItem, ProgramShare
from apps.programs.domain.exceptions import InvalidProgramDataError
from apps.programs.domain.value_objects import (
    ArrangementBlock,
    ArrangementSettings,
    BreakRule,
    CellValue,
    ColumnTitle,
    GroupingAxis,
    ItemDuration,
    ItemTitle,
    PerformanceOrder,
    ProgramItemKind,
    ProgramItemProgress,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
    parse_column_refs,
)
from apps.programs.infrastructure.models import (
    ProgramColumnModel,
    ProgramItemModel,
    ProgramModel,
    ProgramShareModel,
)

__all__ = ["ProgramMapper"]


class ProgramMapper:
    """Maps program rows to the aggregate and back."""

    @staticmethod
    def to_entity(
        model: ProgramModel,
        *,
        items: list[ProgramItemModel],
        shares: list[ProgramShareModel],
        columns: list[ProgramColumnModel] | None = None,
    ) -> Program:
        """Rebuild the aggregate from its root row and its live children."""
        return Program.rehydrate(
            program_id=model.id,
            competition_id=model.competition_id,
            name=ProgramName(model.name),
            created_at=model.created_at,
            updated_at=model.updated_at,
            nomination_id=model.nomination_id,
            starts_at=model.starts_at,
            buffer=TimeBuffer(int(model.buffer_seconds)),
            items=[ProgramMapper.item_to_entity(row) for row in sorted(items, key=lambda row: row.position)],
            shares=[ProgramMapper._share_to_entity(row) for row in sorted(shares, key=lambda row: row.created_at)],
            custom_columns=[ProgramMapper._column_to_entity(row) for row in sorted(columns or [], key=lambda row: row.position)],
            numbers_issued=int(model.numbers_issued),
            numbers_frozen_at=model.numbers_frozen_at,
            deleted_at=model.deleted_at,
            version=model.version,
            arrangement=ProgramMapper._arrangement_to_entity(model.arrangement),
            rebuilt_at=model.rebuilt_at,
        )

    @staticmethod
    def root_fields(program: Program) -> dict[str, Any]:
        """The root row's columns (id excluded - it is the lookup key)."""
        return {
            "competition_id": program.competition_id,
            "nomination_id": program.nomination_id,
            "name": str(program.name),
            "starts_at": program.starts_at,
            "buffer_seconds": program.buffer.seconds,
            "numbers_issued": program.numbers_issued,
            "numbers_frozen_at": program.numbers_frozen_at,
            "arrangement": ProgramMapper._arrangement_fields(program.arrangement),
            "rebuilt_at": program.rebuilt_at,
            "created_at": program.created_at,
            "updated_at": program.updated_at,
            "deleted_at": program.deleted_at,
            "version": program.version,
        }

    @staticmethod
    def item_fields(item: ProgramItem, *, position: int) -> dict[str, Any]:
        """One item row's columns, stamped with its 1-based ordinal in the program.

        ``position`` comes from the aggregate's list on every save; ``number`` comes from
        the item itself and is written once, when the slot is created.
        """
        return {
            "position": position,
            "number": item.number,
            "kind": item.kind.value,
            "title": str(item.title) if item.title is not None else "",
            "duration_seconds": item.duration.seconds,
            "submission_id": item.submission_id,
            "custom_values": {str(column_id): str(value) for column_id, value in item.custom_values.items()},
            "progress": item.progress.value,
        }

    @staticmethod
    def column_fields(column: CustomColumn, *, position: int) -> dict[str, Any]:
        """One custom-column row's fields."""
        return {"position": position, "title": str(column.title)}

    @staticmethod
    def share_fields(share: ProgramShare) -> dict[str, Any]:
        """One public-edition row's own columns (not to be confused with its selection)."""
        return {
            "name": str(share.name),
            "slug": str(share.slug),
            "columns": [ref.key for ref in share.columns],
            "item_ids": [str(item_id) for item_id in share.item_ids],
            "controls_running_order": share.controls_running_order,
        }

    @staticmethod
    def _arrangement_fields(settings: ArrangementSettings | None) -> dict[str, Any]:
        """The generation rules as one JSON object (``{}`` for a hand-built programme)."""
        if settings is None:
            return {}
        return {
            "grouping": [axis.value for axis in settings.grouping],
            "order_within_group": settings.order_within_group.value,
            "break_rule": settings.break_rule.value,
            "break_after_seconds": settings.break_after_seconds,
            "break_after_items": settings.break_after_items,
            "break": ProgramMapper._block_fields(settings.break_block),
            "repeat_gap": settings.repeat_gap,
            "opening": ProgramMapper._block_fields(settings.opens_with),
            "award": ProgramMapper._block_fields(settings.closes_with),
        }

    @staticmethod
    def _block_fields(block: ArrangementBlock | None) -> dict[str, Any] | None:
        if block is None:
            return None
        return {"title": str(block.title), "duration_seconds": block.duration.seconds}

    @staticmethod
    def _arrangement_to_entity(raw: Any) -> ArrangementSettings | None:
        """Read the stored rules back, or ``None`` when they no longer make sense.

        Deliberately forgiving, unlike every other field here: these settings are a
        convenience that prefills a form, not programme data. A grouping axis retired in
        a later release, or a rule whose companion field was dropped, must cost the
        organizer a refilled dialog - never a programme that fails to load.
        """
        if not isinstance(raw, dict) or not raw:
            return None
        try:
            return ArrangementSettings(
                grouping=tuple(GroupingAxis(axis) for axis in raw.get("grouping") or ()),
                order_within_group=PerformanceOrder(str(raw.get("order_within_group"))),
                break_rule=BreakRule(str(raw.get("break_rule"))),
                break_after_seconds=int(raw.get("break_after_seconds") or 0),
                break_after_items=int(raw.get("break_after_items") or 0),
                break_block=ProgramMapper._block_to_entity(raw.get("break")),
                repeat_gap=int(raw.get("repeat_gap") or 0),
                opens_with=ProgramMapper._block_to_entity(raw.get("opening")),
                closes_with=ProgramMapper._block_to_entity(raw.get("award")),
            )
        except (InvalidProgramDataError, TypeError, ValueError):
            return None

    @staticmethod
    def _block_to_entity(raw: Any) -> ArrangementBlock | None:
        if not isinstance(raw, dict):
            return None
        return ArrangementBlock.of(str(raw.get("title") or ""), seconds=int(raw.get("duration_seconds") or 0))

    @staticmethod
    def item_to_entity(row: ProgramItemModel) -> ProgramItem:
        kind = ProgramItemKind(row.kind)
        duration = ItemDuration(int(row.duration_seconds))
        # Rows written before numbers existed fall back to their ordinal, which is what
        # their number would have been anyway.
        number = int(row.number) or int(row.position)
        values = {uuid.UUID(str(key)): CellValue(str(value)) for key, value in (row.custom_values or {}).items()}
        progress = ProgramItemProgress(row.progress or ProgramItemProgress.PENDING.value)
        if kind.binds_performance and row.submission_id is not None:
            return ProgramItem.performance(
                item_id=row.id,
                submission_id=row.submission_id,
                duration=duration,
                number=number,
                custom_values=values,
                progress=progress,
            )
        # A row that lost its submission (or was written as a block) rehydrates as a
        # titled block: the slot keeps its place rather than failing the whole load.
        return ProgramItem.block(
            item_id=row.id,
            kind=kind if not kind.binds_performance else ProgramItemKind.TECHNICAL,
            title=ItemTitle(row.title or "Без названия"),
            duration=duration,
            number=number,
            custom_values=values,
            progress=progress,
        )

    @staticmethod
    def _column_to_entity(row: ProgramColumnModel) -> CustomColumn:
        return CustomColumn(_id=row.id, _title=ColumnTitle(row.title))

    @staticmethod
    def _share_to_entity(row: ProgramShareModel) -> ProgramShare:
        return ProgramShare(
            _id=row.id,
            _name=ShareName(row.name),
            _slug=PublicSlug(row.slug),
            # Rows written before columns existed have none, and the entity reads that
            # as "the default columns" rather than as "no columns".
            _columns=parse_column_refs(row.columns or []),
            _item_ids=tuple(uuid.UUID(str(item_id)) for item_id in row.item_ids or []),
            _controls_running_order=bool(row.controls_running_order),
            _created_at=row.created_at,
        )
