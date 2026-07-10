"""``DjangoCompetitionRepository`` — the ORM adapter for the ``Competition`` aggregate.

The concrete implementation of the
:class:`~apps.competitions.application.interfaces.CompetitionRepository` port
(ARCH-001 §7.2, §7.3): the **single** component permitted to touch the Django ORM on
behalf of the ``Competition`` aggregate. Use cases speak only ``Competition`` and
value objects; this adapter turns those into root/child model queries and back via
:class:`CompetitionMapper`.

**Aggregate persistence.** The ``Competition`` owns a large child graph (taxonomy,
admission/pricing rules, regulations, documents, services, contacts, information
blocks). :meth:`save` writes the root row **and** synchronizes every child table in
one transaction: each aggregate-owned collection is replaced wholesale (delete then
bulk-insert), which is correct and race-free under the root's optimistic lock.
Child rows keep their domain ids across the rewrite, so references stay stable.

**Optimistic concurrency.** The aggregate owns its ``version`` and bumps it once per
mutation. The root write is conditional on the *previous* version, so a write built
from a stale read updates zero rows and is surfaced as
:class:`ConcurrencyConflictError` instead of silently clobbering a concurrent change.

**Soft delete.** Reads exclude soft-deleted rows (``deleted_at IS NOT NULL``); rows
are never physically removed at the aggregate level.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Model

from apps.competitions.domain.entities import Competition
from apps.competitions.domain.value_objects import CompetitionId, Season
from apps.competitions.infrastructure.mappers import CompetitionChildRows, CompetitionMapper
from apps.competitions.infrastructure.models import (
    AdditionalServiceModel,
    AdmissionRuleModel,
    AgeCategoryModel,
    CategoryModel,
    CompetitionModel,
    ContactModel,
    DisciplineModel,
    DocumentModel,
    InformationBlockModel,
    ParticipantGroupModel,
    PricingRuleModel,
    RegulationModel,
)

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoCompetitionRepository"]


class DjangoCompetitionRepository:
    """Django ORM adapter implementing the ``CompetitionRepository`` port.

    Stateless and cheap to construct. Structurally satisfies the port (no
    ``Protocol`` inheritance — the seam is structural by design).
    """

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, competition_id: CompetitionId) -> Competition | None:
        """Return the competition with ``competition_id`` (whole aggregate), or ``None``."""
        try:
            model = CompetitionModel.objects.filter(pk=competition_id.value, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load competition {competition_id}.") from exc
        if model is None:
            return None
        return self._hydrate(model)

    def exists(self, competition_id: CompetitionId) -> bool:
        """Whether a non-deleted competition with ``competition_id`` exists."""
        try:
            return CompetitionModel.objects.filter(pk=competition_id.value, deleted_at__isnull=True).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to check existence of {competition_id}.") from exc

    def list_by_season(self, season: Season) -> Sequence[Competition]:
        """Return all non-deleted competitions in ``season`` (newest first)."""
        try:
            models = list(CompetitionModel.objects.filter(season=season.value, deleted_at__isnull=True).order_by("-created_at"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to list competitions for season {season.value}.") from exc
        return [self._hydrate(model) for model in models]

    def list_all(self) -> Sequence[Competition]:
        """Return all non-deleted competitions (newest first)."""
        try:
            models = list(CompetitionModel.objects.filter(deleted_at__isnull=True).order_by("-created_at"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list competitions.") from exc
        return [self._hydrate(model) for model in models]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save(self, competition: Competition) -> None:
        """Persist ``competition`` and its whole graph (insert or update), honouring its version.

        The root write is conditional on the *previous* version: an ``UPDATE … WHERE
        id=? AND version=current-1`` maps a stale read to zero affected rows, surfaced
        as :class:`ConcurrencyConflictError`. A freshly created aggregate is inserted.
        Either branch then replaces the competition's child rows with the aggregate's
        current set, all inside one transaction.
        """
        model = CompetitionMapper.to_model(competition)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        previous_version = competition.version - 1
        pk = competition.id.value
        try:
            with transaction.atomic():
                updated = CompetitionModel.objects.filter(pk=pk, version=previous_version).update(**update_values)
                if not updated:
                    if CompetitionModel.objects.filter(pk=pk).exists():
                        raise ConcurrencyConflictError(
                            f"Competition {competition.id} was modified concurrently; expected version {previous_version}."
                        )
                    CompetitionModel.objects.create(**values)
                self._sync_children(pk, CompetitionMapper.to_child_rows(competition))
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist competition {competition.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist competition {competition.id}.") from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _hydrate(model: CompetitionModel) -> Competition:
        """Load every child collection for ``model`` and reconstruct the aggregate."""
        pk = model.id
        return CompetitionMapper.to_domain(
            model,
            categories=CategoryModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            disciplines=DisciplineModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            age_categories=AgeCategoryModel.objects.filter(competition_id=pk).order_by("min_age", "id"),
            participant_groups=ParticipantGroupModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            admission_rules=AdmissionRuleModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            pricing_rules=PricingRuleModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            regulations=RegulationModel.objects.filter(competition_id=pk).order_by("publication_date", "id"),
            documents=DocumentModel.objects.filter(competition_id=pk).order_by("sort_order", "created_at", "id"),
            additional_services=AdditionalServiceModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            contacts=ContactModel.objects.filter(competition_id=pk).order_by("created_at", "id"),
            information_blocks=InformationBlockModel.objects.filter(competition_id=pk).order_by("sort_order", "created_at", "id"),
        )

    @staticmethod
    def _sync_children(pk: uuid.UUID, rows: CompetitionChildRows) -> None:
        """Replace every child table's rows for ``pk`` with the aggregate's current set."""
        _replace(CategoryModel, pk, rows.categories)
        _replace(DisciplineModel, pk, rows.disciplines)
        _replace(AgeCategoryModel, pk, rows.age_categories)
        _replace(ParticipantGroupModel, pk, rows.participant_groups)
        _replace(AdmissionRuleModel, pk, rows.admission_rules)
        _replace(PricingRuleModel, pk, rows.pricing_rules)
        _replace(RegulationModel, pk, rows.regulations)
        _replace(DocumentModel, pk, rows.documents)
        _replace(AdditionalServiceModel, pk, rows.additional_services)
        _replace(ContactModel, pk, rows.contacts)
        _replace(InformationBlockModel, pk, rows.information_blocks)

    @staticmethod
    def _column_values(model: CompetitionModel) -> dict[str, object]:
        """Flatten a mapped root ``CompetitionModel`` into its concrete column values."""
        return {field.attname: getattr(model, field.attname) for field in CompetitionModel._meta.concrete_fields}


def _replace(model_cls: type[Model], pk: uuid.UUID, rows: Sequence[Model]) -> None:
    """Delete a competition's rows in ``model_cls`` and bulk-insert the current set."""
    model_cls._default_manager.filter(competition_id=pk).delete()
    if rows:
        model_cls._default_manager.bulk_create(rows)
