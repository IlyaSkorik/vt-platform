"""``ParticipantMapper`` — the ACL between the ``Participant`` aggregate and its ORM rows.

This mapper is the **single** component permitted to know both the framework-free
domain (:class:`apps.participants.domain.entities.Participant` and its value objects)
and the Django persistence models
(:class:`~apps.participants.infrastructure.models.ParticipantModel` and
:class:`~apps.participants.infrastructure.models.GuardianLinkModel`). Keeping that
knowledge in one place is what lets the domain stay ignorant of the ORM and the ORM
stay ignorant of business rules (ARCH-001 §4.1, §7.2, §14).

Its whole job is translation:

* :meth:`to_domain` — a participant row **plus its guardian-link rows** → aggregate,
  via :meth:`Participant.rehydrate` (no re-validation, no events, ``version`` kept).
* :meth:`to_model` — aggregate → a **new, unsaved** ``ParticipantModel`` (parent only).
* :meth:`update_model` — project an aggregate onto an **existing** ``ParticipantModel``.
* :meth:`to_guardian_link_models` — the aggregate's guardian links → **unsaved** child
  rows keyed to the participant, for the repository to synchronize.

What it deliberately does **not** do: validate business rules, run a workflow,
publish events, query, or call ``save()``. Persistence timing and child-row
synchronization belong to the repository.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.participants.domain.entities import Participant
from apps.participants.domain.value_objects import (
    ActorReference,
    ActorType,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianLink,
    GuardianRelationshipType,
    InstitutionAuthority,
    InstitutionId,
    ParticipantId,
    ParticipantStatus,
    PersonName,
    RelationshipStatus,
    TeacherId,
)
from apps.participants.infrastructure.models import GuardianLinkModel, ParticipantModel

__all__ = ["ParticipantMapper"]


class ParticipantMapper:
    """Bidirectional translator between the ``Participant`` aggregate and its rows.

    Stateless: every method is a pure, side-effect-free projection, so the mapper
    holds no state and can be used as a namespace of static methods.
    """

    @staticmethod
    def to_domain(model: ParticipantModel, links: Iterable[GuardianLinkModel]) -> Participant:
        """Reconstruct the ``Participant`` aggregate from its row and guardian-link rows.

        Delegates to :meth:`Participant.rehydrate`, which re-runs no invariant and
        emits no events: the stored state was already valid when written. Each column
        is wrapped back into its value object; ``NULL`` columns (institution/teacher,
        consent, and the lifecycle timestamps) map to ``None``.
        """
        authority: InstitutionAuthority | None = None
        if model.institution_id is not None:
            authority = InstitutionAuthority(
                institution_id=InstitutionId.from_uuid(model.institution_id),
                teacher_id=(
                    TeacherId.from_uuid(model.teacher_id)
                    if model.teacher_id is not None
                    else None
                ),
            )
        consent: ConsentReference | None = None
        if model.consent_id is not None and model.consent_version is not None:
            consent = ConsentReference(
                consent_id=model.consent_id, consent_version=model.consent_version
            )
        guardian_links = tuple(
            GuardianLink(
                guardian_id=GuardianId.from_uuid(link.guardian_id),
                relationship_type=GuardianRelationshipType(link.relationship_type),
                status=RelationshipStatus(link.status),
                established_at=link.established_at,
            )
            for link in links
        )
        return Participant.rehydrate(
            participant_id=ParticipantId.from_uuid(model.id),
            name=PersonName(
                first_name=model.first_name,
                last_name=model.last_name,
                middle_name=model.middle_name,
            ),
            date_of_birth=DateOfBirth(model.date_of_birth),
            display_alias=DisplayAlias(model.display_alias),
            created_by=ActorReference(
                actor_id=model.created_by_id, actor_type=ActorType(model.created_by_type)
            ),
            status=ParticipantStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            guardian_links=guardian_links,
            institution_authority=authority,
            consent=consent,
            verified_at=model.verified_at,
            activated_at=model.activated_at,
            archived_at=model.archived_at,
            erased_at=model.erased_at,
        )

    @staticmethod
    def to_model(entity: Participant) -> ParticipantModel:
        """Build a brand-new, **unsaved** ``ParticipantModel`` (parent only) from an aggregate."""
        return ParticipantModel(**ParticipantMapper._to_columns(entity))

    @staticmethod
    def update_model(model: ParticipantModel, entity: Participant) -> ParticipantModel:
        """Project ``entity`` onto an existing parent ``model`` in place, returning it."""
        for field, value in ParticipantMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_guardian_link_models(entity: Participant) -> list[GuardianLinkModel]:
        """Build **unsaved** guardian-link rows for the aggregate, keyed to the participant."""
        return [
            GuardianLinkModel(
                participant_id=entity.id.value,
                guardian_id=link.guardian_id.value,
                relationship_type=link.relationship_type.value,
                status=link.status.value,
                established_at=link.established_at,
            )
            for link in entity.guardian_links
        ]

    @staticmethod
    def _to_columns(entity: Participant) -> dict[str, object]:
        """Flatten an aggregate into the ``ParticipantModel`` column values (parent only)."""
        authority = entity.institution_authority
        consent = entity.consent
        teacher = authority.teacher_id if authority is not None else None
        return {
            "id": entity.id.value,
            "first_name": entity.name.first_name,
            "last_name": entity.name.last_name,
            "middle_name": entity.name.middle_name,
            "date_of_birth": entity.date_of_birth.value,
            "display_alias": entity.display_alias.value,
            "status": entity.status.value,
            "created_by_id": entity.created_by.actor_id,
            "created_by_type": entity.created_by.actor_type.value,
            "institution_id": authority.institution_id.value if authority is not None else None,
            "teacher_id": teacher.value if teacher is not None else None,
            "consent_id": consent.consent_id if consent is not None else None,
            "consent_version": consent.consent_version if consent is not None else None,
            "verified_at": entity.verified_at,
            "activated_at": entity.activated_at,
            "archived_at": entity.archived_at,
            "erased_at": entity.erased_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }
