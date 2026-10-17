"""Mass print-package generation.

A competition assigns a template per genre, and a genre's nomination may assign
one of its own, so generation runs per *target*: the caller resolves each slice of
the competition to the template it prints on (see :class:`NominationTarget`), and
the service creates a diploma for every performance in that slice that lacks one
(snapshot + number + verification token, no degree), renders each pre-ceremony
PDF, and bundles them all into one ZIP the organizer prints from. Existing
diplomas are skipped; any still missing a print PDF is rendered so the ZIP is a
complete printable set. Each sheet is filed under the name it will be handed out
by — see :func:`_sheet_name`.

The ZIP also carries a ``МЕСТА`` folder — see :data:`PLACE_SHEETS_DIR`.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
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

__all__ = ["PLACE_SHEETS_DIR", "BatchResult", "DiplomaBatchGenerationService", "NominationTarget"]

_TOKEN_BYTES = 32

#: Folder inside the print archive holding the overprint sheets, one per degree.
#:
#: The package is printed before the ceremony, so every diploma in it leaves the
#: Степень field empty — the jury has not decided yet. The degree still has to reach
#: a sheet that is already printed, and the way that is done in practice is to feed
#: it back through the printer over a page that is blank apart from the degree. This
#: folder is that set of pages: for each template in the run, one sheet per degree
#: the jury can award, each drawn exactly where and how that template places its
#: Степень field.
PLACE_SHEETS_DIR = "МЕСТА"

#: Characters that would turn a template's name into extra nesting (or escape the
#: folder) if it were used verbatim as an archive path component.
_ARCNAME_SEPARATORS = str.maketrans({"/": "-", "\\": "-", ":": "-"})


def _arc_component(name: str, *, fallback: str) -> str:
    """One safe path component of an archive entry, from a name a human typed."""
    cleaned = name.translate(_ARCNAME_SEPARATORS).strip().strip(".")
    return cleaned or fallback


def _sheet_name(diploma: Diploma) -> str:
    """What one diploma is called inside the print archive.

    Whoever opens this archive is sorting a stack of paper into envelopes, and they
    do it by who the sheet is for — so the collective's name (or the performer's
    ФИО) leads. The number follows because two Ивановых Анны at one festival are
    ordinary, and because the number is what the register is reconciled against: it
    is the file's identity, just not the first thing a human needs to read.

    An individual sheet inside a collective is named after that member — the
    collective's own sheet carries no member, and then the performer's name is the
    act's.
    """
    snapshot = diploma.snapshot
    member = snapshot.member.full_name if snapshot.member is not None else ""
    who = _arc_component(member or snapshot.participant.display_name, fallback="")
    return f"{who} — {diploma.number}.pdf" if who else f"{diploma.number}.pdf"


@dataclass(frozen=True, slots=True)
class NominationTarget:
    """One slice of a genre to generate for, with the template it prints on.

    A genre is one target while all of it prints on one sheet. Once a nomination
    assigns a template of its own it becomes a target too — ``discipline_id`` names
    it — and the genre's remaining target lists it in ``excluded_discipline_ids``
    so the two cover the genre exactly once between them.
    """

    category_id: uuid.UUID
    template_id: uuid.UUID
    #: The one nomination this target prints, or None for "the rest of the genre".
    discipline_id: uuid.UUID | None = None
    #: Nominations of this genre that print on a template of their own. Only ever
    #: set on the genre-wide target, which is the one that must skip them.
    excluded_discipline_ids: tuple[uuid.UUID, ...] = ()


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
        place_degrees: Sequence[str] = (),
    ) -> None:
        """``place_degrees`` are the degrees the ``МЕСТА`` folder gets a sheet for, in
        the order they should be printed in. Passed in rather than known here: which
        awards exist is the Results context's vocabulary, and this service is not
        allowed to reach for it (see ``infrastructure.acl.award_vocabulary``). Empty
        means no such folder."""
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace
        self._numbers = numbers
        self._place_degrees = tuple(place_degrees)

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
        # Load (and validate) each target's template once — two targets of one genre
        # often share it.
        assets_by_template: dict[uuid.UUID, TemplateAssets] = {}
        for target in targets:
            if target.template_id in assets_by_template:
                continue
            assets = self._workspace.load_template(target.template_id)
            if assets is None:
                raise PrintTemplateNotReadyError("У выбранного шаблона нет PDF-подложки для печати.")
            assets_by_template[target.template_id] = assets

        created = 0
        skipped = 0
        items: list[tuple[str, str]] = []

        for target in targets:
            assets = assets_by_template[target.template_id]
            entries = self._snapshots.list_submission_ids(
                competition_id,
                category_id=target.category_id,
                discipline_id=target.discipline_id,
                exclude_discipline_ids=target.excluded_discipline_ids,
            )
            for submission_id in entries:
                diploma = self._repository.get_by_submission(submission_id)
                if diploma is None:
                    built = self._snapshots.build(submission_id)
                    if built is None:
                        continue
                    diploma = Diploma.create(
                        diploma_id=self._repository.new_id(),
                        number=self._numbers.next_number(competition_year=built.competition_year or now.year),
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
                        assets=assets,
                        snapshot=diploma.snapshot,
                        number=diploma.number,
                        verification_token=diploma.verification_token,
                    )
                    path = self._workspace.store_pdf(competition_id=competition_id, number=diploma.number, data=data)
                    diploma = diploma.with_print_pdf(path, now=now)
                    self._repository.update(diploma)

                pdf_path = diploma.print_pdf_path
                if pdf_path is None:
                    # Not reachable while the branch above always stores a path, but
                    # skipping beats putting a null into the ZIP manifest: one
                    # unrenderable diploma must not fail the whole batch.
                    continue
                items.append((_sheet_name(diploma), pdf_path))

        zip_path = self._workspace.store_zip(
            competition_id=competition_id,
            items=items,
            extras=self._place_sheets(assets_by_template),
        )
        return BatchResult(created=created, skipped=skipped, zip_path=zip_path)

    def _place_sheets(self, assets_by_template: dict[uuid.UUID, TemplateAssets]) -> list[tuple[str, bytes]]:
        """The ``МЕСТА`` folder: one blank overprint sheet per template per degree.

        Keyed by template, not by nomination — the sheet is a function of where the
        template puts its Степень field, so two nominations printed over the same
        template need one set between them. Each folder is named after its template,
        which is how the organizer knows which stack of blanks a sheet belongs to, and
        each sheet is numbered by seniority so the folder reads Гран-при first rather
        than alphabetically.

        A template with no Степень field contributes nothing: there is nowhere on it
        for a degree to land, so an empty sheet would only be printed by mistake.
        """
        if not self._place_degrees:
            return []
        sheets: list[tuple[str, bytes]] = []
        used: set[str] = set()
        for index, assets in enumerate(assets_by_template.values(), start=1):
            rendered = [
                (position, degree, data)
                for position, degree in enumerate(self._place_degrees, start=1)
                if (data := self._workspace.render_place_sheet(assets=assets, degree=degree)) is not None
            ]
            if not rendered:
                continue  # No Степень field on this template — nowhere to overprint.
            folder = _arc_component(assets.name, fallback=f"Шаблон {index}")
            # Two templates may carry the same name; keeping both under it would put two
            # different sets of sheets in one folder, so the later one is distinguished.
            while folder in used:
                folder = f"{folder} ({index})"
            used.add(folder)
            for position, degree, data in rendered:
                name = _arc_component(degree, fallback=str(position))
                sheets.append((f"{PLACE_SHEETS_DIR}/{folder}/{position}. {name}.pdf", data))
        return sheets
