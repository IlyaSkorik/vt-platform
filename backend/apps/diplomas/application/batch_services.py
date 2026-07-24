"""Mass print-package generation.

For a competition + assigned template, create a diploma for every performance
that lacks one (snapshot + number + verification token, no degree), render each
pre-ceremony PDF, and bundle them into a ZIP the organizer prints from. Diplomas
that already exist are not re-created (skipped); any diploma still missing its
print PDF is rendered so the ZIP is a complete printable set.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from apps.diplomas.application.interfaces import (
    DiplomaRepository,
    DiplomaSnapshotSource,
    PrintPackageWorkspace,
)
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.exceptions import PrintTemplateNotReadyError

__all__ = ["BatchResult", "DiplomaBatchGenerationService"]

_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class BatchResult:
    created: int
    skipped: int
    zip_path: str


class DiplomaBatchGenerationService:
    """Generate the print package for a competition (offline preparation)."""

    def __init__(
        self,
        *,
        repository: DiplomaRepository,
        snapshots: DiplomaSnapshotSource,
        workspace: PrintPackageWorkspace,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace

    def generate_print_package(
        self, *, competition_id: uuid.UUID, template_id: uuid.UUID, now: datetime
    ) -> BatchResult:
        """Create missing diplomas, render print PDFs, and bundle the ZIP.

        Raises :class:`PrintTemplateNotReadyError` if the template has no PDF.
        """
        assets = self._workspace.load_template(template_id)
        if assets is None:
            raise PrintTemplateNotReadyError("The template has no PDF to print over.")

        created = 0
        skipped = 0
        items: list[tuple[str, str]] = []

        for submission_id in self._snapshots.list_submission_ids(competition_id):
            diploma = self._repository.get_by_submission(submission_id)
            if diploma is None:
                built = self._snapshots.build(submission_id)
                if built is None:
                    continue
                diploma = Diploma.create(
                    diploma_id=self._repository.new_id(),
                    number=self._repository.next_number(),
                    verification_token=secrets.token_urlsafe(_TOKEN_BYTES),
                    competition_id=built.competition_id,
                    submission_id=submission_id,
                    template_id=template_id,
                    snapshot=built.snapshot,
                    now=now,
                )
                self._repository.add(diploma)
                created += 1
            else:
                skipped += 1

            if not diploma.print_pdf_path:
                data = self._workspace.render(
                    assets=assets, snapshot=diploma.snapshot, number=diploma.number
                )
                path = self._workspace.store_pdf(
                    competition_id=competition_id, number=diploma.number, data=data
                )
                diploma = diploma.with_print_pdf(path, now=now)
                self._repository.update(diploma)

            items.append((f"{diploma.number}.pdf", diploma.print_pdf_path))

        zip_path = self._workspace.store_zip(competition_id=competition_id, items=items)
        return BatchResult(created=created, skipped=skipped, zip_path=zip_path)
