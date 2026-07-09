"""``DjangoParticipantRepository`` — the ORM-backed adapter for the ``Participant`` aggregate.

The concrete implementation of the
:class:`~apps.participants.application.interfaces.ParticipantRepository` port
(ARCH-001 §7.2, §7.3): the **single** component permitted to touch the Django ORM
on behalf of the ``Participant`` aggregate. Use cases speak only ``Participant`` and
value objects, and this adapter turns those into ``ParticipantModel`` /
``GuardianLinkModel`` queries and back via :class:`ParticipantMapper`.

What lives here, and nowhere else (ARCH-001 §14): querying the ORM, opening a
:func:`~django.db.transaction.atomic` block for a consistent read-then-write,
invoking the mapper, and translating every Django exception into a
:mod:`~apps.participants.infrastructure.repositories.exceptions` type.

**Aggregate persistence.** The ``Participant`` aggregate owns its guardian
relationships, so :meth:`save` persists the parent row **and** synchronizes the
guardian-link child rows in one transaction: the small, aggregate-owned collection
is replaced wholesale, which is correct and race-free under the parent's optimistic
lock.

**Optimistic concurrency.** The aggregate owns its ``version`` and bumps it once per
mutation. :meth:`save` writes conditionally on the *previous* version, so a write
built from a stale read updates zero rows and is surfaced as
:class:`ConcurrencyConflictError` instead of silently clobbering a concurrent change.

**Active-alias semantics.** Alias lookups exclude soft-deleted and erased rows, so a
display alias is unique only among live participants and frees up once a participant
is erased (mirroring ``participants_unique_active_display_alias``).
"""

from __future__ import annotations

import uuid

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Q

from apps.participants.domain.entities import Participant
from apps.participants.domain.value_objects import DisplayAlias, ParticipantId
from apps.participants.infrastructure.mappers import ParticipantMapper
from apps.participants.infrastructure.models import GuardianLinkModel, ParticipantModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoParticipantRepository"]

_ACTIVE_ALIAS = Q(deleted_at__isnull=True) & ~Q(status="erased")


class DjangoParticipantRepository:
    """Django ORM adapter implementing the ``ParticipantRepository`` port.

    Stateless and cheap to construct. Structurally satisfies
    :class:`~apps.participants.application.interfaces.ParticipantRepository` (it does
    not inherit the ``Protocol`` — the port is structural by design, keeping the
    application core free of a dependency edge pointing at this module).
    """

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, participant_id: ParticipantId) -> Participant | None:
        """Return the participant with ``participant_id`` (any state), or ``None``."""
        try:
            model = ParticipantModel.objects.get(pk=participant_id.value)
        except ParticipantModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load participant {participant_id}.") from exc
        return ParticipantMapper.to_domain(model, self._links_for(participant_id.value))

    def get_by_display_alias(self, alias: DisplayAlias) -> Participant | None:
        """Return the active, non-erased participant with ``alias``, or ``None``."""
        try:
            model = ParticipantModel.objects.filter(_ACTIVE_ALIAS, display_alias=alias.value).get()
        except ParticipantModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load participant by display alias.") from exc
        return ParticipantMapper.to_domain(model, self._links_for(model.id))

    def exists(self, participant_id: ParticipantId) -> bool:
        """Whether a participant row with ``participant_id`` is stored (any state)."""
        try:
            return ParticipantModel.objects.filter(pk=participant_id.value).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to check existence of {participant_id}.") from exc

    def exists_by_display_alias(self, alias: DisplayAlias) -> bool:
        """Whether an active, non-erased participant currently uses ``alias``."""
        try:
            return ParticipantModel.objects.filter(_ACTIVE_ALIAS, display_alias=alias.value).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to check display alias.") from exc

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save(self, participant: Participant) -> None:
        """Persist ``participant`` (insert or update) and synchronize its guardian links.

        The write is conditional on the *previous* version: an ``UPDATE … WHERE id=?
        AND version=current-1`` maps a stale read to zero affected rows, surfaced as
        :class:`ConcurrencyConflictError`. A freshly created aggregate is inserted.
        Either branch then replaces the participant's guardian-link rows with the
        aggregate's current set, all inside one transaction.
        """
        model = ParticipantMapper.to_model(participant)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        previous_version = participant.version - 1
        try:
            with transaction.atomic():
                updated = ParticipantModel.objects.filter(pk=participant.id.value, version=previous_version).update(**update_values)
                if not updated:
                    if ParticipantModel.objects.filter(pk=participant.id.value).exists():
                        raise ConcurrencyConflictError(
                            f"Participant {participant.id} was modified concurrently; expected version {previous_version}."
                        )
                    ParticipantModel.objects.create(**values)
                self._sync_guardian_links(participant)
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist participant {participant.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist participant {participant.id}.") from exc

    def delete(self, participant: Participant) -> None:
        """Soft-delete ``participant``: stamp ``deleted_at`` on the row; never remove it.

        Rows are retained for audit and to free the display alias for reuse. Only an
        **active** (non-soft-deleted) row is affected; a repeat call is an idempotent
        no-op. ``version`` is advanced so the marker participates in optimistic
        concurrency.
        """
        deleted_at = participant.erased_at or participant.updated_at
        try:
            with transaction.atomic():
                ParticipantModel.objects.filter(pk=participant.id.value, deleted_at__isnull=True).update(
                    deleted_at=deleted_at, version=F("version") + 1
                )
        except IntegrityError as exc:  # pragma: no cover - defensive
            raise IntegrityViolationError(f"Failed to delete participant {participant.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete participant {participant.id}.") from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _links_for(participant_pk: uuid.UUID) -> list[GuardianLinkModel]:
        """Load a participant's guardian-link rows in a stable order."""
        return list(GuardianLinkModel.objects.filter(participant_id=participant_pk).order_by("created_at", "id"))

    @staticmethod
    def _sync_guardian_links(participant: Participant) -> None:
        """Replace the participant's guardian-link rows with the aggregate's current set."""
        GuardianLinkModel.objects.filter(participant_id=participant.id.value).delete()
        rows = ParticipantMapper.to_guardian_link_models(participant)
        if rows:
            GuardianLinkModel.objects.bulk_create(rows)

    @staticmethod
    def _column_values(model: ParticipantModel) -> dict[str, object]:
        """Flatten a mapped ``ParticipantModel`` into its concrete column values."""
        return {field.attname: getattr(model, field.attname) for field in ParticipantModel._meta.concrete_fields}
