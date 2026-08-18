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

**Individual diplomas.** An entry whose applicant named the people in its collective gets
one more diploma per person, alongside the collective's own — same award, same protocol,
each naming one child. They are issued here, by the same publication and under the same
three rules, because they are diplomas: numbered, verifiable, and true only once the jury
has decided. Two conditions gate them, and both are the organizer's or the applicant's
choice rather than this service's:

* the applicant named the roster (see ``SnapshotBuild.members``) — an empty roster is a
  request never made, not a failure;
* the nomination assigns an ``INDIVIDUAL_DIPLOMA`` template, which is a separate layout
  because it carries one field the collective's sheet cannot: the member's own ФИО.

Either one missing means the collective's diploma is issued exactly as before. Nothing
about this path can fail the publication of the results.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from apps.diplomas.application.interfaces import (
    AssignedTemplate,
    DiplomaRepository,
    DiplomaSnapshotSource,
    PrintPackageWorkspace,
    TemplateAssets,
    TemplateAssignments,
)
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import DiplomaSnapshot, MemberSnapshot

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
    #: How many individual diplomas this entry's collective now holds — nought unless
    #: the applicant named its members and the nomination has a template for them.
    #: Counted separately from the performance's own diploma, which is the one thing
    #: the protocol itself is about.
    individual_count: int = 0


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

        Each entry that named the people in its collective also has an individual diploma
        issued per person, when the nomination has a template for them — see the module
        docstring.
        """
        assigned = self._assignments.for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=DocumentType.DIPLOMA,
        )
        assets = None
        if assigned is not None and assigned.template_type is DocumentType.DIPLOMA:
            assets = self._workspace.load_template(assigned.template_id)

        # The individual-diploma slot of the same nomination, resolved once for the run.
        # Absent for every nomination whose organizer has not designed that sheet, which
        # is the normal case and costs the collective's diploma nothing.
        individual = self._assignments.for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=DocumentType.INDIVIDUAL_DIPLOMA,
        )
        individual_assets = None
        if individual is not None and individual.template_type is DocumentType.INDIVIDUAL_DIPLOMA:
            individual_assets = self._workspace.load_template(individual.template_id)

        outcomes: list[AwardOutcome] = []
        for submission_id, degree in awards:
            diploma = self._repository.get_by_submission(submission_id)
            created = False
            # Built lazily and at most once per entry: an existing diploma needs no
            # snapshot, but the roster of a collective is only on the live submission.
            built = None
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

            individual_count = 0
            if individual is not None and individual_assets is not None:
                if built is None:
                    built = self._snapshots.build(submission_id)
                if built is not None:
                    individual_count = self._issue_individual_diplomas(
                        collective=diploma,
                        members=built.members,
                        competition_year=built.competition_year or now.year,
                        template=individual,
                        assets=individual_assets,
                        degree=degree,
                        now=now,
                    )

            outcomes.append(
                AwardOutcome(
                    submission_id=submission_id,
                    number=diploma.number,
                    degree=degree,
                    created=created,
                    file_url=file_url,
                    individual_count=individual_count,
                )
            )
        return outcomes

    def _issue_individual_diplomas(
        self,
        *,
        collective: Diploma,
        members: tuple[str, ...],
        competition_year: int,
        template: AssignedTemplate,
        assets: TemplateAssets,
        degree: str,
        now: datetime,
    ) -> int:
        """Issue one diploma per named member of a collective; return how many.

        Each member's sheet is built from the **collective's own frozen snapshot** plus
        that one name, so the two documents cannot disagree about the ensemble, the work,
        the nomination or the event — an individual diploma is the collective's diploma
        with one more line on it. Only the member is added; nothing is taken away, which
        is why the individual template is free to place every field the collective's does.

        Correction works exactly as it does for the collective's diploma: a second call
        writes the new degree onto the same rows, keeping each member's number, token and
        URL. A member removed from the roster after publication keeps the diploma they
        were already given — revoking an issued document is a deliberate act, not a
        side effect of an edit.
        """
        if not members or not policy_for(template.template_type).per_member:
            return 0
        issued = 0
        for name in members:
            member = self._repository.get_by_submission(
                collective.submission_id,
                DocumentType.INDIVIDUAL_DIPLOMA,
                name,
            )
            if member is None:
                member = Diploma.create(
                    diploma_id=self._repository.new_id(),
                    number=self._numbers.next_number(competition_year=competition_year),
                    verification_token=secrets.token_urlsafe(_TOKEN_BYTES),
                    competition_id=collective.competition_id,
                    submission_id=collective.submission_id,
                    template_id=template.template_id,
                    snapshot=self._member_snapshot(collective.snapshot, name),
                    now=now,
                    document_type=DocumentType.INDIVIDUAL_DIPLOMA,
                    recipient=name,
                )
                self._repository.add(member)
            member = member.with_degree(degree, now=now)
            data = self._workspace.render(
                assets=assets,
                snapshot=member.snapshot,
                number=member.number,
                verification_token=member.verification_token,
            )
            file_url = self._workspace.store_official_pdf(
                competition_id=member.competition_id,
                number=member.number,
                data=data,
            )
            self._repository.update(member.issued(file_url, now=now))
            issued += 1
        return issued

    @staticmethod
    def _member_snapshot(base: DiplomaSnapshot, name: str) -> DiplomaSnapshot:
        """The collective's snapshot addressed to one of its members."""
        return replace(base, member=MemberSnapshot(full_name=name))
