"""Translation between the :class:`Protocol` aggregate and its two tables.

The only place that knows both shapes (ARCH-001 §7.2). Two things are worth watching:

* **Order.** The aggregate's row *list* is authoritative, so writing enumerates it and
  reading sorts by the recorded ``position`` - a row's ordinal is a projection of the
  list, never an input to it.
* **The empty slug.** The domain models "never published" as ``slug is None`` and the
  column models it as ``""``, because a nullable unique column and a partial index are
  two ways of saying the same thing and the blank string is the one the constraint reads
  more clearly. This module is where the two representations meet, and the only place
  either has to be known about.
"""

from __future__ import annotations

from typing import Any

from apps.results.domain.entities import Protocol, ProtocolRow
from apps.results.domain.value_objects import (
    AwardKind,
    ProtocolName,
    ProtocolStatus,
    PublicSlug,
    PublishedSnapshot,
    parse_columns,
)
from apps.results.infrastructure.models import ProtocolModel, ProtocolRowModel

__all__ = ["ProtocolMapper"]


class ProtocolMapper:
    """Maps protocol rows to the aggregate and back."""

    @staticmethod
    def to_entity(model: ProtocolModel, *, rows: list[ProtocolRowModel]) -> Protocol:
        """Rebuild the aggregate from its root row and its live rows."""
        return Protocol.rehydrate(
            protocol_id=model.id,
            competition_id=model.competition_id,
            nomination_id=model.nomination_id,
            name=ProtocolName(model.name),
            created_at=model.created_at,
            updated_at=model.updated_at,
            status=ProtocolStatus(model.status),
            rows=[ProtocolMapper._row_to_entity(row) for row in sorted(rows, key=lambda row: row.position)],
            # Rows written before a column selection existed have none, and the entity
            # reads that as "the default columns" rather than as "no columns".
            public_columns=parse_columns(model.public_columns or []),
            slug=PublicSlug(model.slug) if model.slug else None,
            revision=int(model.revision),
            published_at=model.published_at,
            published_version=int(model.published_version),
            published_snapshot=PublishedSnapshot.from_dict(model.published_snapshot) if model.published_snapshot else None,
            seeded_from_program_id=model.seeded_from_program_id,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def root_fields(protocol: Protocol) -> dict[str, Any]:
        """The root row's columns (id excluded - it is the lookup key)."""
        return {
            "competition_id": protocol.competition_id,
            "nomination_id": protocol.nomination_id,
            "name": str(protocol.name),
            "status": protocol.status.value,
            "public_columns": [column.value for column in protocol.public_columns],
            "slug": str(protocol.slug) if protocol.slug is not None else "",
            "revision": protocol.revision,
            "published_at": protocol.published_at,
            "published_version": protocol.published_version,
            "published_snapshot": protocol.published_snapshot.to_dict() if protocol.published_snapshot is not None else None,
            "seeded_from_program_id": protocol.seeded_from_program_id,
            "created_at": protocol.created_at,
            "updated_at": protocol.updated_at,
            "deleted_at": protocol.deleted_at,
            "version": protocol.version,
        }

    @staticmethod
    def row_fields(row: ProtocolRow, *, position: int) -> dict[str, Any]:
        """One row's columns, stamped with its 1-based ordinal in the protocol.

        ``position`` comes from the aggregate's list on every save; ``number`` comes from
        the row itself and is written once, when the line is created.
        """
        return {
            "position": position,
            "number": row.number,
            "submission_id": row.submission_id,
            "award": row.award.value if row.award is not None else None,
        }

    @staticmethod
    def _row_to_entity(row: ProtocolRowModel) -> ProtocolRow:
        return ProtocolRow(
            _id=row.id,
            _submission_id=row.submission_id,
            # Rows written before numbers existed fall back to their ordinal, which is
            # what their number would have been anyway.
            _number=int(row.number) or int(row.position),
            _award=AwardKind(row.award) if row.award else None,
        )
