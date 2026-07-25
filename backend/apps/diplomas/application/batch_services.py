"""Mass print-package generation.

A competition assigns a template **per nomination**, so generation runs per
nomination: for each requested nomination, the caller supplies its assigned
template, and the service creates a diploma for every performance in that
nomination that lacks one (snapshot + number + verification token, no degree),
renders each pre-ceremony PDF, and bundles them all into one ZIP the organizer
prints from. Existing diplomas are skipped; any still missing a print PDF is
rendered so the ZIP is a complete printable set.
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
    TemplateAssets,
)
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.exceptions import PrintTemplateNotReadyError

__all__ = ["BatchResult", "DiplomaBatchGenerationService", "NominationTarget"]

_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class NominationTarget:
    """One nomination to generate for, with its assigned template."""

    category_id: uuid.UUID
    template_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class BatchResult:
    created: int
    skipped: int
    zip_path: str


class DiplomaBatchGenerationService:
    """Generate the print package for selected nominations (offline preparation)."""

    def __init__(
        self,
        *,
        repository: DiplomaRepository,
        snapshots: DiplomaSnapshotSource,
        workspace: PrintPackageWorkspace,
        numbers: DiplomaNumberService,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace
        self._numbers = numbers

    def generate_print_package(
        self,
        *,
        competition_id: uuid.UUID,
        targets: list[NominationTarget],
        now: datetime,
        force: bool = False,
    ) -> BatchResult:
        """Create missing diplomas per nomination, render print PDFs, bundle a ZIP.

        With ``force`` the print PDF is re-rendered even for diplomas that already
        have one (e.g. after a template change) — creation/skip counts are
        unchanged, only the rendered file is refreshed. Raises
        :class:`PrintTemplateNotReadyError` if any target's template has no PDF
        (checked up front so nothing is half-generated).
        """
        # Load (and validate) each nomination's template once.
        assets_by_template: dict[uuid.UUID, TemplateAssets] = {}
        for target in targets:
            if target.template_id in assets_by_template:
                continue
            assets = self._workspace.load_template(target.template_id)
            if assets is None:
                raise PrintTemplateNotReadyError("A selected template has no PDF to print over.")
            assets_by_template[target.template_id] = assets

        created = 0
        skipped = 0
        items: list[tuple[str, str]] = []

        for target in targets:
            assets = assets_by_template[target.template_id]
            for submission_id in self._snapshots.list_submission_ids(
                competition_id, category_id=target.category_id
            ):
                diploma = self._repository.get_by_submission(submission_id)
                if diploma is None:
                    built = self._snapshots.build(submission_id)
                    if built is None:
                        continue
                    diploma = Diploma.create(
                        diploma_id=self._repository.new_id(),
                        number=self._numbers.next_number(
                            competition_year=built.competition_year or now.year
                        ),
                        verification_token=secrets.token_urlsafe(_TOKEN_BYTES),
                        competition_id=built.competition_id,
                        submission_id=submission_id,
                        template_id=target.template_id,
                        snapshot=built.snapshot,
                        now=now,
                    )
                    self._repository.add(diploma)
                    created += 1
                else:
                    skipped += 1

                if force or not diploma.print_pdf_path:
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
