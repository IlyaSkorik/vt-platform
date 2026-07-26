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
* **Immediate publication.** :meth:`IssuedDocument.with_pdf` stamps
  ``published_at`` when the policy says so, and the document reaches the
  participant's cabinet with no organizer step.

Adding an unnumbered third kind (e.g. ``CERTIFICATE``) needs **no change here** —
only a new :class:`DocumentType` member and its policy row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from apps.diplomas.application.interfaces import (
    DiplomaSnapshotSource,
    IssuedDocumentRepository,
    PrintPackageWorkspace,
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


def _addressees(
    snapshot: DiplomaSnapshot, policy: DocumentPolicy
) -> list[tuple[str, DiplomaSnapshot]]:
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
    return [
        (teacher.name, replace(snapshot, teachers=(teacher,)))
        for teacher in snapshot.teachers
        if teacher.name.strip()
    ]


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
    ) -> IssuedDocumentResult:
        """Render this kind of document for every performance in the nomination.

        Uses the template the nomination assigns to *this kind* — so «Вокал» may
        print a blue thank-you while «Хореография» prints a gold one. Documents
        that already have a PDF are left alone unless ``force`` re-renders them.

        Raises :class:`TemplateNotAssignedError` when the nomination has no
        template of this kind, :class:`TemplateTypeMismatchError` when the assigned
        template was authored for a different kind, and
        :class:`PrintTemplateNotReadyError` when it has no backing PDF — all
        checked before anything is written, so a run is never half-done.
        """
        policy = policy_for(document_type)
        if policy.is_registry_document:
            # Numbered, verifiable documents belong to the Diploma aggregate and
            # its own service; routing one here would bypass numbering entirely.
            raise TemplateTypeMismatchError(
                "Registry documents are generated by the diploma print package, not here."
            )
        if policy.numbered:
            # No unnumbered-registry hybrid exists yet. Fail loudly rather than
            # silently printing a blank number: a numbered kind needs a number
            # source injected here and a prefix of its own.
            raise TemplateTypeMismatchError(
                f"{document_type.value} is numbered; this service issues unnumbered documents only."
            )

        assigned = self._assignments.for_nomination(
            competition_id=competition_id, category_id=category_id, document_type=document_type
        )
        if assigned is None:
            raise TemplateNotAssignedError("This nomination has no template for that document type.")
        if assigned.template_type is not document_type:
            raise TemplateTypeMismatchError(
                "The assigned template was made for a different document type."
            )

        assets = self._workspace.load_template(assigned.template_id)
        if assets is None:
            raise PrintTemplateNotReadyError("The selected template has no PDF to print over.")

        # Prepared once for the whole run rather than per document.
        printable = replace(assets, fields=_prepare_layout(assets.fields, policy))

        created = 0
        regenerated = 0
        without_recipient = 0
        for submission_id in self._snapshots.list_submission_ids(
            competition_id, category_id=category_id
        ):
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
                    continue
                else:
                    regenerated += 1

                # No number and no token: an unnumbered, unverifiable document. The
                # renderer draws neither, because neither resolves to a value.
                data = self._workspace.render(
                    assets=printable,
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
                self._repository.update(document.with_pdf(path, now=now))

        return IssuedDocumentResult(
            created=created,
            regenerated=regenerated,
            without_recipient=without_recipient,
            document_type=document_type,
        )
