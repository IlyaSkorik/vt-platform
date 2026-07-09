"""Result DTOs for the Participants application layer.

Immutable output shapes returned by the use cases. They are the boundary in the
*other* direction: a handler renders the domain ``Participant`` aggregate into a
flat, serialization-agnostic :class:`ParticipantDto` (with its guardian links as
:class:`GuardianLinkDto` rows) and wraps it — together with the domain events the
operation produced — in an :class:`OperationResultDto`.

Framework-free (stdlib only): value objects are flattened to primitives, so no
outer layer needs to import the domain to read a result. All DTOs are ``frozen``
and ``slots``, and events are held as an immutable ``tuple``.

Events-collected-not-published: :attr:`OperationResultDto.events` carries the
events the aggregate returned. Handlers **do not** publish them; a future Unit of
Work commits the aggregate and hands these events to the outbox / event dispatcher
(ARCH-001 §4.8). For now they simply travel out with the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.participants.domain.entities import Participant
from apps.participants.domain.events import DomainEvent
from apps.participants.domain.value_objects import GuardianLink

__all__ = ["GuardianLinkDto", "OperationResultDto", "ParticipantDto"]


@dataclass(frozen=True, slots=True)
class GuardianLinkDto:
    """A flat read view of a guardian relationship inside the aggregate."""

    guardian_id: str
    relationship_type: str
    status: str
    established_at: datetime | None

    @classmethod
    def from_link(cls, link: GuardianLink) -> GuardianLinkDto:
        """Project a :class:`GuardianLink` value object into a DTO."""
        return cls(
            guardian_id=link.guardian_id.json(),
            relationship_type=link.relationship_type.value,
            status=link.status.value,
            established_at=link.established_at,
        )


@dataclass(frozen=True, slots=True)
class ParticipantDto:
    """A flat, immutable read view of the ``Participant`` aggregate.

    Every field is a primitive or stdlib type so the DTO is trivially serializable
    and free of any domain dependency at the call site. The real-name fields are
    carried here as the application boundary; the presentation layer is responsible
    for restricting who may see them (PRT-006) and for showing judging only the
    ``display_alias`` (JDG-006).
    """

    id: str
    display_alias: str
    status: str
    first_name: str
    last_name: str
    middle_name: str | None
    full_name: str
    date_of_birth: str
    created_by_id: str
    created_by_type: str
    institution_id: str | None
    teacher_id: str | None
    consent_id: str | None
    consent_version: str | None
    guardian_links: tuple[GuardianLinkDto, ...]
    verified_at: datetime | None
    activated_at: datetime | None
    archived_at: datetime | None
    erased_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_participant(cls, participant: Participant) -> ParticipantDto:
        """Project ``participant`` into a DTO, flattening its value objects."""
        authority = participant.institution_authority
        consent = participant.consent
        teacher_id = authority.teacher_id if authority is not None else None
        return cls(
            id=participant.id.json(),
            display_alias=participant.display_alias.value,
            status=participant.status.value,
            first_name=participant.name.first_name,
            last_name=participant.name.last_name,
            middle_name=participant.name.middle_name,
            full_name=participant.name.full,
            date_of_birth=participant.date_of_birth.isoformat(),
            created_by_id=str(participant.created_by.actor_id),
            created_by_type=participant.created_by.actor_type.value,
            institution_id=authority.institution_id.json() if authority is not None else None,
            teacher_id=teacher_id.json() if teacher_id is not None else None,
            consent_id=str(consent.consent_id) if consent is not None else None,
            consent_version=consent.consent_version if consent is not None else None,
            guardian_links=tuple(GuardianLinkDto.from_link(link) for link in participant.guardian_links),
            verified_at=participant.verified_at,
            activated_at=participant.activated_at,
            archived_at=participant.archived_at,
            erased_at=participant.erased_at,
            created_at=participant.created_at,
            updated_at=participant.updated_at,
            version=participant.version,
        )


@dataclass(frozen=True, slots=True)
class OperationResultDto:
    """The outcome of a Participants command: the affected participant plus its events.

    ``participant`` is the post-operation state; ``events`` are the domain events
    the aggregate produced, collected for a future Unit of Work / outbox to publish
    (never published by the handler itself).
    """

    participant: ParticipantDto
    events: tuple[DomainEvent, ...]
