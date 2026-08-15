"""Ports the Diplomas application depends on (implemented by infrastructure).

Kept as ``Protocol`` structural types so the domain/application never import
Django; the concrete adapters live in ``apps.diplomas.infrastructure``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.issued_document import IssuedDocument
from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = [
    "AssignedTemplate",
    "DiplomaNumberSequence",
    "DiplomaRepository",
    "DiplomaSnapshotSource",
    "IssuedDocumentRepository",
    "PrintPackageWorkspace",
    "SnapshotBuild",
    "TemplateAssets",
    "TemplateAssignments",
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

    def list_submission_ids(self, competition_id: uuid.UUID, *, category_id: uuid.UUID | None = None) -> list[uuid.UUID]:
        """Live submission ids of a competition — one performance each. Narrowed to
        a nomination (category) when ``category_id`` is given."""
        ...


@dataclass(frozen=True, slots=True)
class AssignedTemplate:
    """The template filling one document slot of a nomination, with its own type.

    ``template_type`` is the template's declared type, which the caller checks
    against the requested slot — the two are stored separately and must agree.
    """

    template_id: uuid.UUID
    template_type: DocumentType


class TemplateAssignments(Protocol):
    """Read port over the assignment table, narrowed to one document kind.

    Keeps the generation service free of the assignment's persistence shape: it
    asks "which template fills this nomination's thank-you slot?" and gets an id.
    """

    def for_nomination(self, *, competition_id: uuid.UUID, category_id: uuid.UUID, document_type: DocumentType) -> AssignedTemplate | None:
        """The template assigned to this nomination for this kind, or None."""
        ...


class IssuedDocumentRepository(Protocol):
    """Persistence port for the ``IssuedDocument`` aggregate."""

    def new_id(self) -> uuid.UUID:
        """Mint a fresh, time-ordered document id."""
        ...

    def add(self, document: IssuedDocument) -> None:
        """Persist a new document."""
        ...

    def update(self, document: IssuedDocument) -> None:
        """Persist changes to an existing document."""
        ...

    def get_for_submission(self, submission_id: uuid.UUID, document_type: DocumentType, recipient: str = "") -> IssuedDocument | None:
        """The live document of this kind for a performance and recipient, or None.

        ``recipient`` is empty for a kind issued once per performance."""
        ...

    def list_by_competition(self, competition_id: uuid.UUID, document_type: DocumentType) -> list[IssuedDocument]:
        """Every live document of this kind for a competition, newest first."""
        ...


@dataclass(frozen=True, slots=True)
class TemplateAssets:
    """A template's print inputs: its placed fields and its backing PDF bytes.

    ``name`` is the template as the organizer named it ("Вокал A4"). It is carried
    for the archive rather than for rendering: the place sheets are grouped per
    template, and a folder named after the template is what tells the printer which
    blanks a sheet overprints.
    """

    fields: list[dict[str, object]]
    backing_pdf: bytes
    name: str = ""


class PrintPackageWorkspace(Protocol):
    """Infra for rendering + storing print PDFs and the ZIP (reportlab/pypdf +
    file storage). Kept behind a port so the batch service stays Django-free."""

    def load_template(self, template_id: uuid.UUID) -> TemplateAssets | None:
        """The template's fields + backing PDF, or None if it has no PDF yet."""
        ...

    def render(
        self,
        *,
        assets: TemplateAssets,
        snapshot: DiplomaSnapshot,
        number: str,
        verification_token: str,
    ) -> bytes:
        """Render one diploma PDF from the template assets and a snapshot.

        ``verification_token`` is the diploma's own token; the adapter turns it
        into the verification URL behind the QR code (the public domain is
        infrastructure configuration, not application knowledge). An **empty**
        token means the document is not verifiable, so no URL is built at all."""
        ...

    def render_place_sheet(self, *, assets: TemplateAssets, degree: str) -> bytes | None:
        """Render the overprint sheet for one degree: a blank page of the template's
        geometry carrying nothing but that degree, where the template places it.

        ``None`` when the template has no Степень field — nowhere to overprint."""
        ...

    def store_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        """Persist a diploma's **print** PDF (pre-ceremony, no degree); return its path."""
        ...

    def store_official_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        """Persist the participant's own copy (post-ceremony, with the degree).

        Separate from :meth:`store_pdf` because both copies are legitimately wanted at
        once — the organizer prints the blanks before the ceremony and the participant
        downloads the awarded one after — so one key for both would mean publishing the
        results destroyed the print set. Re-rendering a corrected degree replaces the
        object in place, keeping the URL the participant already has."""
        ...

    def store_document_pdf(
        self,
        *,
        competition_id: uuid.UUID,
        document_type: str,
        submission_id: uuid.UUID,
        data: bytes,
        recipient: str = "",
    ) -> str:
        """Persist a non-diploma document's PDF; return its ``/media/…`` path.

        Keyed by kind, performance and recipient rather than by number, because
        these documents have no number and a per-teacher kind issues several per
        performance. Separate from :meth:`store_pdf` so thank-you letters do not
        land in the diploma print tree."""
        ...

    def store_zip(self, *, competition_id: uuid.UUID, items: list[tuple[str, str]], extras: Sequence[tuple[str, bytes]] = ()) -> str:
        """Bundle ``(arcname, media_path)`` pairs into a ZIP; return its path.

        ``extras`` are ``(arcname, bytes)`` members written straight into the archive
        rather than copied out of storage. The place sheets go in that way: they are
        derived from the template, not from any diploma, so there is nothing to store
        them under and nothing that would ever fetch them on their own."""
        ...

    def store_documents_zip(self, *, competition_id: uuid.UUID, document_type: str, items: list[tuple[str, str]]) -> str:
        """Bundle one kind's documents into a ZIP; return its path.

        Separate from :meth:`store_zip` for the same reason as
        :meth:`store_document_pdf`: the archive lives with the kind it holds, so a
        thank-you bundle never lands in — or overwrites — the diploma print set."""
        ...
