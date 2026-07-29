"""Writing the jury's result onto a diploma, and issuing it to the participant.

The **only** path by which ``award.degree`` is ever set. It exists as its own service in
this context rather than as code in whoever decided the result, because three rules belong
to Diplomas and to nowhere else:

* a diploma is created if the performance has none, so a result never has nothing to land
  on — a competition run entirely online has no print package to have created one;
* the degree is written onto the existing snapshot, leaving the number, the verification
  token and every other frozen value alone (``Diploma.with_degree``);
* the participant's own copy is rendered and the diploma becomes ``ISSUED``, which is what
  makes it appear in "Мои документы". Before that moment the participant has no document,
  because before the results are published there is no result to put on one.

**Correction is a first-class path, not an exception.** Awarding twice is expected: results
get corrected, and the second call re-renders the same diploma with the new degree, keeping
its number, its token and the URL the participant already holds. Nothing here issues a
second document for one performance.

A nomination with no diploma template assigned is the one partial outcome allowed: the
degree is recorded and the PDF is not, so the results still stand and the organizer can
assign a template and re-publish. Failing the whole publication over a missing template
would hold a festival's results hostage to a layout.
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
    TemplateAssignments,
)
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.entities import Diploma

__all__ = ["AwardOutcome", "DiplomaAwardService"]

_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class AwardOutcome:
    """What happened to one performance's diploma.

    ``file_url`` is ``None`` when the degree was recorded but no participant copy could be
    rendered — see the module docstring. ``created`` says whether this call is what brought
    the diploma into existence, which is what tells an organizer whether a published
    nomination's diplomas came from the print package or from the publication itself.
    """

    submission_id: uuid.UUID
    number: str
    degree: str
    created: bool
    file_url: str | None = None


class DiplomaAwardService:
    """Records results on diplomas and issues them to their participants."""

    def __init__(
        self,
        *,
        repository: DiplomaRepository,
        snapshots: DiplomaSnapshotSource,
        workspace: PrintPackageWorkspace,
        assignments: TemplateAssignments,
        numbers: DiplomaNumberService,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._workspace = workspace
        self._assignments = assignments
        self._numbers = numbers

    def award(
        self,
        *,
        competition_id: uuid.UUID,
        category_id: uuid.UUID,
        awards: list[tuple[uuid.UUID, str]],
        now: datetime,
    ) -> list[AwardOutcome]:
        """Write ``(submission id, degree)`` onto each diploma and issue it.

        Returns one outcome per performance whose diploma now carries the degree. A
        performance whose submission has been deleted from Applications entirely is
        skipped: there is no snapshot to build a diploma from and nobody to issue it to.
        The caller sees the gap as a shortfall in the count rather than as an exception,
        because the protocol is still a true record of what the jury decided.
        """
        assigned = self._assignments.for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=DocumentType.DIPLOMA,
        )
        assets = None
        if assigned is not None and assigned.template_type is DocumentType.DIPLOMA:
            assets = self._workspace.load_template(assigned.template_id)

        outcomes: list[AwardOutcome] = []
        for submission_id, degree in awards:
            diploma = self._repository.get_by_submission(submission_id)
            created = False
            if diploma is None:
                if assigned is None:
                    # No diploma, and no template to make one against. The result stands in
                    # the protocol; the document waits for a template.
                    continue
                built = self._snapshots.build(submission_id)
                if built is None:
                    continue
                diploma = Diploma.create(
                    diploma_id=self._repository.new_id(),
                    number=self._numbers.next_number(competition_year=built.competition_year or now.year),
                    verification_token=secrets.token_urlsafe(_TOKEN_BYTES),
                    competition_id=built.competition_id,
                    submission_id=submission_id,
                    template_id=assigned.template_id,
                    snapshot=built.snapshot,
                    now=now,
                )
                self._repository.add(diploma)
                created = True

            diploma = diploma.with_degree(degree, now=now)
            file_url: str | None = None
            if assets is not None:
                # Rendered from the diploma's own snapshot, which now carries the degree —
                # the participant's copy differs from the print copy in exactly that.
                data = self._workspace.render(
                    assets=assets,
                    snapshot=diploma.snapshot,
                    number=diploma.number,
                    verification_token=diploma.verification_token,
                )
                file_url = self._workspace.store_official_pdf(
                    competition_id=diploma.competition_id,
                    number=diploma.number,
                    data=data,
                )
                diploma = diploma.issued(file_url, now=now)
            # ``add`` above stored the pre-degree state, so a freshly created diploma is
            # updated for the same reason an existing one is.
            self._repository.update(diploma)
            outcomes.append(
                AwardOutcome(
                    submission_id=submission_id,
                    number=diploma.number,
                    degree=degree,
                    created=created,
                    file_url=file_url,
                )
            )
        return outcomes
