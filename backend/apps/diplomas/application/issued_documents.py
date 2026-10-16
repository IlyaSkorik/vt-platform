"""Generation for document kinds that are not diplomas.

One service for every non-registry kind, driven by
:class:`~apps.diplomas.domain.document_types.DocumentPolicy` rather than by the
kind itself. It reuses the diploma pipeline wholesale — the same
:class:`DiplomaSnapshotSource` for data, the same :class:`PrintPackageWorkspace`
for rendering and storage — and copies none of it. The diploma's own service
(:mod:`apps.diplomas.application.batch_services`) is untouched.

What actually differs per kind is expressed as data, not branches:

* **No QR.** ``qr_block`` fields are dropped from the layout for a kind whose
  policy is not ``verifiable``, so no verification URL is ever built and the
  renderer needs no new flag.
* **No number.** The renderer is given an empty number, so a ``diploma.number``
  binding resolves to nothing and — by the renderer's existing rule that a field
  with no value is not drawn — simply does not appear.
* **No degree.** A kind that does not award one leaves the snapshot's award
  untouched, and the same "no value, no field" rule omits any Степень field.
* **Immediate publication — when asked for.** For a kind whose policy allows it,
  :meth:`IssuedDocument.with_pdf` stamps ``published_at`` and the document reaches
  the participant's cabinet with no separate organizer step. A run may withhold
  that (``publish=False``) to prepare sheets for printing without showing them;
  a later publishing run picks those up without re-rendering them.

Adding an unnumbered third kind (e.g. ``CERTIFICATE``) needs **no change here** —
only a new :class:`DocumentType` member and its policy row.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from apps.diplomas.application.interfaces import (
    DiplomaSnapshotSource,
    IssuedDocumentRepository,
    PrintPackageWorkspace,
    TemplateAssets,
    TemplateAssignments,
)
from apps.diplomas.domain.document_types import DocumentPolicy, DocumentType, policy_for
from apps.diplomas.domain.exceptions import (
    PrintTemplateNotReadyError,
    TemplateNotAssignedError,
    TemplateTypeMismatchError,
)
from apps.diplomas.domain.issued_document import IssuedDocument
from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = ["IssuedDocumentGenerationService", "IssuedDocumentResult"]

#: Field type whose text is the teacher roster.
_TEACHER_FIELD_TYPE = "teacher"

#: Characters a ZIP entry name may not carry, whatever a name field holds.
_UNSAFE_IN_NAME = re.compile(r"[\\/:*?\"<>|\r\n\t]+")


@dataclass(frozen=True, slots=True)
class IssuedDocumentResult:
    """Outcome of one generation run for one nomination.

    Counts **documents**, not performances: a per-teacher kind issues one per
    teacher, so an entry with two teachers contributes two.
    """

    created: int
    regenerated: int
    #: Entries a per-teacher kind could not address because no teacher is named.
    without_recipient: int
    document_type: DocumentType
    #: Entries skipped because neither their nomination nor their genre assigns a
    #: template of this kind. Non-zero only for a genre that has no default and
    #: covers some of its nominations — see the loop in ``generate_for_nomination``.
    without_template: int = 0
    #: Documents this run made visible to participants. Zero for a print-only run,
    #: and the only non-zero count when publishing what an earlier print run left
    #: rendered but unpublished.
    published: int = 0
    #: Every document the nomination now holds, as ``(zip entry name, media path)``
    #: — the whole set, not just what this run rendered, so a bundle built from it
    #: is a complete printable stack even on a re-run that created nothing.
    items: tuple[tuple[str, str], ...] = ()


def _safe(value: str | None) -> str:
    """A name field reduced to something a file name may hold."""
    return _UNSAFE_IN_NAME.sub(" ", str(value or "")).strip()


def _arcname(snapshot: DiplomaSnapshot, recipient: str) -> str:
    """Where one document sits inside the printable ZIP.

    Grouped by nomination and named after the person the sheet is handed to,
    because that is how an organizer sorts a printed stack — the storage key is a
    submission uuid and says nothing to whoever is stuffing envelopes. The
    performance is kept in the name too, so a teacher thanked twice gets two
    distinguishable sheets rather than a bare ``(2)``.
    """
    folder = _safe(snapshot.nomination.title) or "Без жанра"
    participant = _safe(snapshot.participant.display_name) or "Без имени"
    addressee = _safe(recipient)
    stem = f"{addressee} — {participant}" if addressee else participant
    return f"{folder}/{stem}.pdf"


def _addressees(snapshot: DiplomaSnapshot, policy: DocumentPolicy) -> list[tuple[str, DiplomaSnapshot]]:
    """The documents to issue for one performance, as ``(recipient, snapshot)``.

    A thank-you letter is addressed to a person, so an entry naming two teachers
    yields **two** letters — each carrying only its own recipient in the snapshot,
    so the teacher field prints one name rather than the whole roster. An entry with
    no teacher yields nothing: there is nobody to thank.

    For a kind issued once per performance (a diploma) there is a single document
    with no recipient and the snapshot untouched — every teacher stays on the sheet.
    """
    if not policy.per_teacher:
        return [("", snapshot)]
    return [(teacher.name, replace(snapshot, teachers=(teacher,))) for teacher in snapshot.teachers if teacher.name.strip()]


def _prepare_layout(fields: list[dict[str, Any]], policy: DocumentPolicy) -> list[dict[str, Any]]:
    """The layout as this kind of document may print it.

    Two rules, both from the policy:

    * **Drop what the kind may not carry.** A thank-you letter has nothing to
      verify, rank or itemise, so a QR block, a degree or a nomination left over
      from an edited template is removed rather than printed. The editor already
      hides them; this is the guarantee that a template edited before the rule
      existed still prints correctly.
    * **Ask the teacher field for the right format.** Roles are a diploma's way of
      crediting a teacher; a letter thanks a person by name.
    """
    prepared: list[dict[str, Any]] = []
    for field in fields:
        field_type = str(field.get("type") or "")
        if not policy.allows_field(field_type):
            continue
        if field_type == _TEACHER_FIELD_TYPE and not policy.teacher_roles:
            field = {**field, "config": {**(field.get("config") or {}), "roles": False}}
        prepared.append(field)
    return prepared


class IssuedDocumentGenerationService:
    """Generate a nomination's documents of one non-registry kind."""

    def __init__(
        self,
        *,
        repository: IssuedDocumentRepository,
        snapshots: DiplomaSnapshotSource,
        workspace: PrintPackageWorkspace,
        assignments: TemplateAssignments,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace
        self._assignments = assignments

    def generate_for_nomination(
        self,
        *,
        competition_id: uuid.UUID,
        category_id: uuid.UUID,
        document_type: DocumentType,
        now: datetime,
        force: bool = False,
        publish: bool = True,
    ) -> IssuedDocumentResult:
        """Render this kind of document for every performance in the genre.

        Uses the template assigned to *this kind* — so «Вокал» may print a blue
        thank-you while «Хореография» prints a gold one, and a nomination inside
        «Вокал» may print its own instead of the genre's. Documents that already
        have a PDF are left alone unless ``force`` re-renders them.

        ``publish`` decides whether the run also shows its documents to the
        participants. Off, the documents are generated and stored but stay out of
        the cabinets — which is what an organizer wants when preparing sheets to
        print and hand out. On, documents that were rendered by an earlier
        print-only run are published too, without being re-rendered: publishing is
        a step of its own, not a side effect of rendering. Nothing is ever
        *un*published.

        Raises :class:`TemplateNotAssignedError` when neither the genre nor any of
        its nominations has a template of this kind,
        :class:`TemplateTypeMismatchError` when one of them was authored for a
        different kind, and :class:`PrintTemplateNotReadyError` when one has no
        backing PDF — all checked before anything is written, so a run is never
        half-done. An entry whose nomination resolves to no template at all is
        skipped and counted (``without_template``) rather than failing the run.
        """
        policy = policy_for(document_type)
        if policy.is_registry_document:
            # Numbered, verifiable documents belong to the Diploma aggregate and
            # its own service; routing one here would bypass numbering entirely.
            raise TemplateTypeMismatchError("Документы реестра выпускаются из пакета печати дипломов.")
        if policy.numbered:
            # No unnumbered-registry hybrid exists yet. Fail loudly rather than
            # silently printing a blank number: a numbered kind needs a number
            # source injected here and a prefix of its own.
            raise TemplateTypeMismatchError("Этот документ нумеруется и выпускается через печать дипломов.")

        resolved = self._assignments.for_category(competition_id=competition_id, category_id=category_id, document_type=document_type)
        if resolved.is_empty:
            raise TemplateNotAssignedError("Для этого жанра не назначен шаблон такого типа.")

        # Every template the genre can print this kind on is validated and prepared
        # before a single document is written — the same "never half-done" rule as
        # before, now over the genre's default and its nominations' own templates.
        printable: dict[uuid.UUID, TemplateAssets] = {}
        for candidate in resolved.templates():
            if candidate.template_type is not document_type:
                raise TemplateTypeMismatchError("Назначенный шаблон сделан для другого типа документа.")
            assets = self._workspace.load_template(candidate.template_id)
            if assets is None:
                raise PrintTemplateNotReadyError("У выбранного шаблона нет PDF-подложки для печати.")
            # Prepared once per template rather than per document.
            printable[candidate.template_id] = replace(assets, fields=_prepare_layout(assets.fields, policy))

        created = 0
        regenerated = 0
        without_recipient = 0
        without_template = 0
        published = 0
        items: list[tuple[str, str]] = []
        entries = self._snapshots.list_submission_ids(competition_id, category_id=category_id)
        # One lookup for the whole genre: which nomination each entry performs in
        # decides which of the genre's templates its sheet is printed on.
        discipline_of = self._snapshots.discipline_ids(entries)
        for submission_id in entries:
            assigned = resolved.for_discipline(discipline_of.get(submission_id))
            if assigned is None:
                # The genre has no default and this entry's nomination assigns no
                # template of its own. Counted rather than raised: an organizer who
                # designed a sheet for one nomination has not thereby promised one
                # for the rest, and the run still does everything it was asked for.
                without_template += 1
                continue

            built = self._snapshots.build(submission_id)
            if built is None:
                continue

            addressed = _addressees(built.snapshot, policy)
            if not addressed:
                # A per-teacher kind with no teacher named on the entry: there is
                # nobody to address, so nothing is issued. Counted, not silent.
                without_recipient += 1
                continue

            for recipient, snapshot in addressed:
                document = self._repository.get_for_submission(submission_id, document_type, recipient)
                if document is None:
                    document = IssuedDocument.create(
                        document_id=self._repository.new_id(),
                        document_type=document_type,
                        competition_id=built.competition_id,
                        submission_id=submission_id,
                        template_id=assigned.template_id,
                        snapshot=snapshot,
                        now=now,
                        recipient=recipient,
                    )
                    self._repository.add(document)
                    created += 1
                elif document.pdf_path and not force:
                    # Nothing to render — but there may still be something to do: a
                    # letter left unpublished by a print-only run is published here
                    # without touching the PDF the organizer may already have printed.
                    if publish and not document.is_published:
                        self._repository.update(document.publish(now=now))
                        published += 1
                    # It still belongs in the bundle either way: the ZIP is the
                    # nomination's whole printable set, not this run's delta.
                    items.append((_arcname(document.snapshot, recipient), document.pdf_path))
                    continue
                else:
                    regenerated += 1

                # No number and no token: an unnumbered, unverifiable document. The
                # renderer draws neither, because neither resolves to a value.
                data = self._workspace.render(
                    assets=printable[assigned.template_id],
                    snapshot=document.snapshot,
                    number="",
                    verification_token="",
                )
                path = self._workspace.store_document_pdf(
                    competition_id=competition_id,
                    document_type=document_type.value,
                    submission_id=submission_id,
                    recipient=document.recipient,
                    data=data,
                )
                rendered = document.with_pdf(path, now=now, publish=publish)
                if rendered.is_published and not document.is_published:
                    published += 1
                self._repository.update(rendered)
                items.append((_arcname(document.snapshot, recipient), path))

        return IssuedDocumentResult(
            created=created,
            regenerated=regenerated,
            without_recipient=without_recipient,
            without_template=without_template,
            document_type=document_type,
            published=published,
            items=tuple(items),
        )

    def bundle(
        self,
        *,
        competition_id: uuid.UUID,
        document_type: DocumentType,
        items: list[tuple[str, str]],
    ) -> str:
        """Bundle already-generated documents into one ZIP; return its media path.

        The offline half of the same run: these documents reach the participants'
        cabinets on generation regardless, and the archive is what an organizer
        prints and hands out at the ceremony — so bundling is a separate step over
        the run's output, not a different way of generating it.

        Names are made unique across the whole archive, because they are built from
        names people actually share — two entries in one nomination may carry the
        same participant name and thank the same teacher — and a duplicate name in a
        ZIP is one file silently overwriting another on extraction. The same file
        listed twice (a teacher named twice on one entry gets one letter) collapses
        to a single entry instead.
        """
        unique: list[tuple[str, str]] = []
        taken: set[str] = set()
        seen_paths: set[str] = set()
        for arcname, media_path in items:
            if media_path in seen_paths:
                continue
            seen_paths.add(media_path)
            stem, dot, extension = arcname.rpartition(".")
            name = arcname
            index = 2
            while name.casefold() in taken:
                name = f"{stem} ({index}){dot}{extension}"
                index += 1
            taken.add(name.casefold())
            unique.append((name, media_path))
        return self._workspace.store_documents_zip(competition_id=competition_id, document_type=document_type.value, items=unique)
