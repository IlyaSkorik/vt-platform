"""Outbound ports for the Platform bounded context.

Structural :class:`Protocol` seams (ARCH-001 §7.3): the application layer states
what it needs, infrastructure supplies it, and the composition root wires the
two. Nothing here imports Django.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.platform.domain.entities import PlatformAdministrator
from apps.platform.domain.value_objects import PlatformUserId

__all__ = ["Clock", "PlatformAdministratorRepository", "UuidGenerator"]


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, always timezone-aware UTC."""

    def utcnow(self) -> datetime: ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: fresh time-ordered identifiers."""

    def new(self) -> uuid.UUID: ...


@runtime_checkable
class PlatformAdministratorRepository(Protocol):
    """Port: load and persist :class:`PlatformAdministrator` grants."""

    def find_by_user(self, user_id: PlatformUserId) -> PlatformAdministrator | None:
        """Return the grant held by this account — active or revoked — or ``None``."""
        ...

    def list_all(self) -> list[PlatformAdministrator]:
        """Return every grant ever issued, oldest first."""
        ...

    def save(self, administrator: PlatformAdministrator) -> None:
        """Persist the grant (insert or update), honouring its version."""
        ...
