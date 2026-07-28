"""Translation between the :class:`Program` aggregate and its three tables.

The only place that knows both shapes (ARCH-001 §7.2). Order is the one thing worth
watching: the aggregate's item *list* is authoritative, so writing enumerates it and
reading sorts by the recorded ``position`` - a row's ordinal is a projection of the
list, never an input to it.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.programs.domain.entities import Program, ProgramItem, ProgramShare
from apps.programs.domain.value_objects import (
    ItemDuration,
    ItemTitle,
    ProgramItemKind,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
    parse_columns,
)
from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel, ProgramShareModel

__all__ = ["ProgramMapper"]


class ProgramMapper:
    """Maps program rows to the aggregate and back."""

    @staticmethod
    def to_entity(model: ProgramModel, *, items: list[ProgramItemModel], shares: list[ProgramShareModel]) -> Program:
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
            items=[ProgramMapper._item_to_entity(row) for row in sorted(items, key=lambda row: row.position)],
            shares=[ProgramMapper._share_to_entity(row) for row in sorted(shares, key=lambda row: row.created_at)],
            deleted_at=model.deleted_at,
            version=model.version,
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
            "created_at": program.created_at,
            "updated_at": program.updated_at,
            "deleted_at": program.deleted_at,
            "version": program.version,
        }

    @staticmethod
    def item_fields(item: ProgramItem, *, position: int) -> dict[str, Any]:
        """One item row's columns, stamped with its 1-based ordinal in the program."""
        return {
            "position": position,
            "kind": item.kind.value,
            "title": str(item.title) if item.title is not None else "",
            "duration_seconds": item.duration.seconds,
            "submission_id": item.submission_id,
        }

    @staticmethod
    def share_fields(share: ProgramShare) -> dict[str, Any]:
        """One public-edition row's own columns (not to be confused with its selection)."""
        return {
            "name": str(share.name),
            "slug": str(share.slug),
            "columns": [column.value for column in share.columns],
            "item_ids": [str(item_id) for item_id in share.item_ids],
        }

    @staticmethod
    def _item_to_entity(row: ProgramItemModel) -> ProgramItem:
        kind = ProgramItemKind(row.kind)
        duration = ItemDuration(int(row.duration_seconds))
        if kind.binds_performance and row.submission_id is not None:
            return ProgramItem.performance(item_id=row.id, submission_id=row.submission_id, duration=duration)
        # A row that lost its submission (or was written as a block) rehydrates as a
        # titled block: the slot keeps its place rather than failing the whole load.
        return ProgramItem.block(
            item_id=row.id,
            kind=kind if not kind.binds_performance else ProgramItemKind.TECHNICAL,
            title=ItemTitle(row.title or "Без названия"),
            duration=duration,
        )

    @staticmethod
    def _share_to_entity(row: ProgramShareModel) -> ProgramShare:
        return ProgramShare(
            _id=row.id,
            _name=ShareName(row.name),
            _slug=PublicSlug(row.slug),
            # Rows written before columns existed have none, and the entity reads that
            # as "the default columns" rather than as "no columns".
            _columns=parse_columns(row.columns or []),
            _item_ids=tuple(uuid.UUID(str(item_id)) for item_id in row.item_ids or []),
            _created_at=row.created_at,
        )
