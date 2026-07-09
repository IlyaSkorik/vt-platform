"""Result DTOs for the Identity & Access application layer.

Immutable output shapes returned by command handlers. They are the boundary in
the *other* direction: a handler renders the domain ``User`` aggregate into a
flat, serialization-agnostic :class:`UserDto` and wraps it — together with the
domain events the operation produced — in an :class:`OperationResultDto`.

Framework-free (stdlib only): value objects are flattened to primitives, so no
outer layer needs to import the domain to read a result. Both DTOs are ``frozen``
and ``slots``, and events are held as an immutable ``tuple``.

Events-collected-not-published: :attr:`OperationResultDto.events` carries the
events the aggregate returned. Handlers **do not** publish them; a future Unit of
Work commits the aggregate and hands these events to the outbox / event
dispatcher (ARCH-001 §4.8). For now they simply travel out with the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.identity.domain.entities import User
from apps.identity.domain.events import DomainEvent

__all__ = ["OperationResultDto", "UserDto"]


@dataclass(frozen=True, slots=True)
class UserDto:
    """A flat, immutable read view of the ``User`` aggregate.

    Every field is a primitive or stdlib type so the DTO is trivially
    serializable and free of any domain dependency at the call site. Build it with
    :meth:`from_user`; ``is_locked`` is evaluated against the ``now`` passed in,
    since a temporary lock's status is time-relative.
    """

    id: str
    email: str
    full_name: str
    first_name: str
    last_name: str
    middle_name: str | None
    phone: str | None
    locale: str
    timezone: str
    is_email_verified: bool
    is_phone_verified: bool
    is_locked: bool
    locked_until: datetime | None
    is_deleted: bool
    consent_version: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_user(cls, user: User, *, now: datetime) -> UserDto:
        """Project ``user`` into a DTO, resolving lock status at ``now``."""
        return cls(
            id=user.id.json(),
            email=user.email.value,
            full_name=user.full_name.full,
            first_name=user.full_name.first_name,
            last_name=user.full_name.last_name,
            middle_name=user.full_name.middle_name,
            phone=user.phone.value if user.phone is not None else None,
            locale=user.locale.value,
            timezone=user.timezone.value,
            is_email_verified=user.is_email_verified(),
            is_phone_verified=user.is_phone_verified(),
            is_locked=user.is_locked(now),
            locked_until=user.locked_until,
            is_deleted=user.is_deleted(),
            consent_version=(user.consent_version.value if user.consent_version is not None else None),
            created_at=user.created_at,
            updated_at=user.updated_at,
            version=user.version,
        )


@dataclass(frozen=True, slots=True)
class OperationResultDto:
    """The outcome of an Identity command: the affected user plus its new events.

    ``user`` is the post-operation state; ``events`` are the domain events the
    aggregate produced, collected for a future Unit of Work / outbox to publish
    (never published by the handler itself).
    """

    user: UserDto
    events: tuple[DomainEvent, ...]
