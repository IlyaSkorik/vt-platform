"""Django adapter for :class:`~apps.programs.application.interfaces.ProgramRepository`.

The aggregate is saved as **one unit** inside a transaction: the root row, then its
items and shares synchronized to the aggregate's current contents. Children the
aggregate no longer holds are soft-deleted rather than dropped, so a removed slot or
a revoked link stays auditable - and a revoked slug stays claimed, which is why the
unique constraint on it is unconditional.
"""

from __future__ import annotations

import uuid

from django.db import transaction

from apps.programs.domain.entities import Program
from apps.programs.infrastructure.mappers import ProgramMapper
from apps.programs.infrastructure.models import (
    ProgramColumnModel,
    ProgramItemModel,
    ProgramModel,
    ProgramShareModel,
)

__all__ = ["DjangoProgramRepository"]


class DjangoProgramRepository:
    """Loads and stores :class:`Program` aggregates in PostgreSQL."""

    def get(self, program_id: uuid.UUID) -> Program | None:
        """Load one live program with its live children."""
        model = ProgramModel.objects.filter(id=program_id, deleted_at__isnull=True).first()
        return None if model is None else self._to_entity(model)

    def list_for_competition(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID | None = None) -> tuple[Program, ...]:
        """Every live program of a competition, oldest first (creation order)."""
        rows = ProgramModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True)
        if nomination_id is not None:
            rows = rows.filter(nomination_id=nomination_id)
        return tuple(self._to_entity(model) for model in rows.order_by("created_at"))

    def slug_taken(self, slug: str) -> bool:
        """Whether any share - live or revoked - has ever used this slug."""
        return ProgramShareModel.objects.filter(slug=slug).exists()

    def get_by_slug(self, slug: str) -> tuple[Program, uuid.UUID] | None:
        """Resolve a public link to (program, share id), or ``None``.

        Both the share and its program must be live: revoking either one takes the
        link down, and a soft-deleted program must not stay readable through an old
        public URL.
        """
        share = (
            ProgramShareModel.objects.filter(slug=slug, deleted_at__isnull=True, program__deleted_at__isnull=True).select_related("program").first()
        )
        if share is None:
            return None
        return self._to_entity(share.program), share.id

    @transaction.atomic
    def save(self, program: Program) -> None:
        """Persist the whole aggregate: root row plus synchronized children."""
        ProgramModel.objects.update_or_create(id=program.id, defaults=ProgramMapper.root_fields(program))
        # Columns first: an item's values are keyed by column id, so the columns they
        # refer to should exist by the time the items land.
        self._sync_columns(program)
        self._sync_items(program)
        self._sync_shares(program)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_entity(self, model: ProgramModel) -> Program:
        items = list(ProgramItemModel.objects.filter(program_id=model.id, deleted_at__isnull=True).order_by("position"))
        shares = list(ProgramShareModel.objects.filter(program_id=model.id, deleted_at__isnull=True).order_by("created_at"))
        columns = list(ProgramColumnModel.objects.filter(program_id=model.id, deleted_at__isnull=True).order_by("position"))
        return ProgramMapper.to_entity(model, items=items, shares=shares, columns=columns)

    def _sync_items(self, program: Program) -> None:
        kept: set[uuid.UUID] = set()
        for position, item in enumerate(program.items, start=1):
            kept.add(item.id)
            ProgramItemModel.objects.update_or_create(
                id=item.id,
                defaults={
                    **ProgramMapper.item_fields(item, position=position),
                    "program_id": program.id,
                    "updated_at": program.updated_at,
                    "deleted_at": None,
                },
            )
        ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).exclude(id__in=kept).update(
            deleted_at=program.updated_at,
            updated_at=program.updated_at,
        )

    def _sync_columns(self, program: Program) -> None:
        kept: set[uuid.UUID] = set()
        for position, column in enumerate(program.custom_columns, start=1):
            kept.add(column.id)
            ProgramColumnModel.objects.update_or_create(
                id=column.id,
                defaults={
                    **ProgramMapper.column_fields(column, position=position),
                    "program_id": program.id,
                    "updated_at": program.updated_at,
                    "deleted_at": None,
                },
            )
        ProgramColumnModel.objects.filter(program_id=program.id, deleted_at__isnull=True).exclude(id__in=kept).update(
            deleted_at=program.updated_at,
            updated_at=program.updated_at,
        )

    def _sync_shares(self, program: Program) -> None:
        kept: set[uuid.UUID] = set()
        for share in program.shares:
            kept.add(share.id)
            ProgramShareModel.objects.update_or_create(
                id=share.id,
                defaults={
                    **ProgramMapper.share_fields(share),
                    "program_id": program.id,
                    "updated_at": program.updated_at,
                    "deleted_at": None,
                },
            )
        ProgramShareModel.objects.filter(program_id=program.id, deleted_at__isnull=True).exclude(id__in=kept).update(
            deleted_at=program.updated_at,
            updated_at=program.updated_at,
        )
