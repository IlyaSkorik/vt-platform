"""Django adapter for :class:`~apps.results.application.interfaces.ProtocolRepository`.

The aggregate is saved as **one unit** inside a transaction: the root row, then its rows
synchronized to the aggregate's current contents. A row the aggregate no longer holds is
soft-deleted rather than dropped - a line that was removed from a protocol is exactly the
kind of thing somebody asks about afterwards, and the row still carries the award it had.
"""

from __future__ import annotations

import uuid

from django.db import transaction

from apps.results.domain.entities import Protocol
from apps.results.domain.value_objects import ProtocolStatus
from apps.results.infrastructure.mappers import ProtocolMapper
from apps.results.infrastructure.models import ProtocolModel, ProtocolRowModel

__all__ = ["DjangoProtocolRepository"]


class DjangoProtocolRepository:
    """Loads and stores :class:`Protocol` aggregates in PostgreSQL."""

    def get(self, protocol_id: uuid.UUID) -> Protocol | None:
        """Load one live protocol with its live rows."""
        model = ProtocolModel.objects.filter(id=protocol_id, deleted_at__isnull=True).first()
        return None if model is None else self._to_entity(model)

    def list_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        """Every live protocol of a competition, oldest first (creation order)."""
        rows = ProtocolModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("created_at")
        return tuple(self._to_entity(model) for model in rows)

    def get_for_nomination(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> Protocol | None:
        """The nomination's protocol, or ``None`` - the one-per-nomination check."""
        model = ProtocolModel.objects.filter(
            competition_id=competition_id,
            nomination_id=nomination_id,
            deleted_at__isnull=True,
        ).first()
        return None if model is None else self._to_entity(model)

    def list_published_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        """Every published protocol of a competition, most recently published first.

        Ordered by publication rather than creation: a landing page's "Результаты" reads
        as a list of announcements, and the newest announcement belongs at the top.
        """
        rows = ProtocolModel.objects.filter(
            competition_id=competition_id,
            status=ProtocolStatus.PUBLISHED.value,
            deleted_at__isnull=True,
        ).order_by("-published_at", "created_at")
        return tuple(self._to_entity(model) for model in rows)

    def slug_taken(self, slug: str) -> bool:
        """Whether any protocol - live, unpublished or deleted - has used this slug."""
        if not slug:
            return False
        return ProtocolModel.objects.filter(slug=slug).exists()

    def get_by_slug(self, slug: str) -> Protocol | None:
        """Resolve a public link to its protocol, or ``None``.

        Both liveness rules apply: a soft-deleted protocol and an unpublished one are
        equally gone from the public edge, so unpublishing takes the page down at once and
        an old link cannot keep serving results that were withdrawn.
        """
        if not slug:
            return None
        model = ProtocolModel.objects.filter(
            slug=slug,
            status=ProtocolStatus.PUBLISHED.value,
            deleted_at__isnull=True,
        ).first()
        return None if model is None else self._to_entity(model)

    @transaction.atomic
    def save(self, protocol: Protocol) -> None:
        """Persist the whole aggregate: root row plus synchronized rows."""
        ProtocolModel.objects.update_or_create(id=protocol.id, defaults=ProtocolMapper.root_fields(protocol))
        self._sync_rows(protocol)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_entity(self, model: ProtocolModel) -> Protocol:
        rows = list(ProtocolRowModel.objects.filter(protocol_id=model.id, deleted_at__isnull=True).order_by("position"))
        return ProtocolMapper.to_entity(model, rows=rows)

    def _sync_rows(self, protocol: Protocol) -> None:
        kept: set[uuid.UUID] = set()
        for position, row in enumerate(protocol.rows, start=1):
            kept.add(row.id)
            ProtocolRowModel.objects.update_or_create(
                id=row.id,
                defaults={
                    **ProtocolMapper.row_fields(row, position=position),
                    "protocol_id": protocol.id,
                    "updated_at": protocol.updated_at,
                    "deleted_at": None,
                },
            )
        ProtocolRowModel.objects.filter(protocol_id=protocol.id, deleted_at__isnull=True).exclude(id__in=kept).update(
            deleted_at=protocol.updated_at,
            updated_at=protocol.updated_at,
        )
