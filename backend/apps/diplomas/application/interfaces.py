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

__all__ = [
    "DiplomaNumberSequence",
    "DiplomaRepository",
    "DiplomaSnapshotSource",
    "PrintPackageWorkspace",
    "SnapshotBuild",
    "TemplateAssets",
]


@dataclass(frozen=True, slots=True)
class SnapshotBuild:
    """A built snapshot plus the competition it belongs to (for the diploma row).

    ``competition_year`` is the year the competition is *held* — the year printed
    in the diploma number. ``None`` when the competition has no dates yet; the
    caller then falls back to the creation year.
    """

    competition_id: uuid.UUID
    snapshot: DiplomaSnapshot
    competition_year: int | None = None


class DiplomaNumberSequence(Protocol):
    """Counter port behind the diploma number.

    Implementations must reserve values atomically (one transaction, row lock) so
    that parallel workers never receive the same value for a scope.
    """

    def next_value(self, *, scope: str) -> int:
        """Reserve and return the next counter value for ``scope`` (starts at 1)."""
        ...


class DiplomaRepository(Protocol):
    """Persistence port for the ``Diploma`` aggregate."""

    def new_id(self) -> uuid.UUID:
        """Mint a fresh, time-ordered diploma id."""
        ...

    def exists_for_submission(self, submission_id: uuid.UUID) -> bool:
        """Whether a (live) diploma already exists for this performance."""
        ...

    def add(self, diploma: Diploma) -> None:
        """Persist a new diploma."""
        ...

    def update(self, diploma: Diploma) -> None:
        """Persist changes to an existing diploma."""
        ...

    def get(self, diploma_id: uuid.UUID) -> Diploma | None:
        """Load a diploma by id, or None if it does not exist."""
        ...

    def get_by_submission(self, submission_id: uuid.UUID) -> Diploma | None:
        """Load the (live) diploma for a performance, or None."""
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

    def list_submission_ids(
        self, competition_id: uuid.UUID, *, category_id: uuid.UUID | None = None
    ) -> list[uuid.UUID]:
        """Live submission ids of a competition — one performance each. Narrowed to
        a nomination (category) when ``category_id`` is given."""
        ...


@dataclass(frozen=True, slots=True)
class TemplateAssets:
    """A template's print inputs: its placed fields and its backing PDF bytes."""

    fields: list[dict]
    backing_pdf: bytes


class PrintPackageWorkspace(Protocol):
    """Infra for rendering + storing print PDFs and the ZIP (reportlab/pypdf +
    file storage). Kept behind a port so the batch service stays Django-free."""

    def load_template(self, template_id: uuid.UUID) -> TemplateAssets | None:
        """The template's fields + backing PDF, or None if it has no PDF yet."""
        ...

    def render(
        self, *, assets: TemplateAssets, snapshot: DiplomaSnapshot, number: str
    ) -> bytes:
        """Render one diploma PDF from the template assets and a snapshot."""
        ...

    def store_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        """Persist a diploma PDF; return its ``/media/…`` path."""
        ...

    def store_zip(self, *, competition_id: uuid.UUID, items: list[tuple[str, str]]) -> str:
        """Bundle ``(arcname, media_path)`` pairs into a ZIP; return its path."""
        ...
