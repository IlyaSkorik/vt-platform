"""Ports the Diplomas application depends on (implemented by infrastructure).

Kept as ``Protocol`` structural types so the domain/application never import
Django; the concrete adapters live in ``apps.diplomas.infrastructure``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = ["DiplomaRepository", "DiplomaSnapshotSource", "SnapshotBuild"]


@dataclass(frozen=True, slots=True)
class SnapshotBuild:
    """A built snapshot plus the competition it belongs to (for the diploma row)."""

    competition_id: uuid.UUID
    snapshot: DiplomaSnapshot


class DiplomaRepository(Protocol):
    """Persistence port for the ``Diploma`` aggregate."""

    def new_id(self) -> uuid.UUID:
        """Mint a fresh, time-ordered diploma id."""
        ...

    def next_number(self) -> str:
        """Reserve the next permanent, unique diploma number."""
        ...

    def exists_for_submission(self, submission_id: uuid.UUID) -> bool:
        """Whether a (live) diploma already exists for this performance."""
        ...

    def add(self, diploma: Diploma) -> None:
        """Persist a new diploma."""
        ...

    def get(self, diploma_id: uuid.UUID) -> Diploma | None:
        """Load a diploma by id, or None if it does not exist."""
        ...

    def list_by_competition(self, competition_id: uuid.UUID) -> list[Diploma]:
        """Every diploma of a competition, newest first (the registry view)."""
        ...


class DiplomaSnapshotSource(Protocol):
    """ACL over the Applications/Competitions contexts: builds the frozen snapshot
    a diploma is created from, and checks that a template exists."""

    def template_exists(self, template_id: uuid.UUID) -> bool:
        """Whether the referenced template is in the library."""
        ...

    def build(self, submission_id: uuid.UUID) -> SnapshotBuild | None:
        """Resolve the submission's data into a snapshot, or None if it is gone.

        ``award.degree`` is left ``None`` — the jury result is filled in later."""
        ...
