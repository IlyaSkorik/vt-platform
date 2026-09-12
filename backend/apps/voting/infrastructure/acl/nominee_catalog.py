"""``DjangoNomineeCatalog`` — the Voting context's window onto a festival.

Reads the Programs context (a running order and its rows) and the Applications
context (what each row's act actually is) and hands back
:class:`~apps.voting.application.interfaces.CatalogNominee` values in *this*
context's language. Everything outward of this module — the aggregate, the use
cases, the API — is written as if the nominees simply arrived as flat data
(ARCH-001 §13.3, Anti-Corruption Layer).

Which is not a fiction: for a standalone ballot they really do arrive as flat
data, typed in or read out of a spreadsheet. This module exists so that the case
where a festival *is* on the platform takes the same path as the one where it is
not, rather than becoming a second kind of ballot.

Which rows may be seeded is a decision this module owns: only performances, and
only ones the audience will actually see. A break, an opening or an awards
ceremony is not somebody the audience votes for.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.programs.infrastructure.models import ProgramItemKindChoices, ProgramItemModel, ProgramModel
from apps.voting.application.interfaces import CatalogNominee

__all__ = ["DjangoNomineeCatalog"]

#: How many performers fit on a card before it stops being readable from row twelve.
_NAMES_ON_A_CARD = 2


def _clean(value: object) -> str:
    return " ".join(str(value).split()).strip() if isinstance(value, str) else ""


def _person(entry: object) -> str:
    """One participant's display name, however the submission spelled it.

    Mirrors the Programs context's reader rather than importing it: the two
    contexts must stay free to disagree about what a performer is called.
    """
    if not isinstance(entry, dict):
        return ""
    display = _clean(entry.get("display_name"))
    if display:
        return display
    return " ".join(part for part in (_clean(entry.get("last_name")), _clean(entry.get("first_name"))) if part)


class DjangoNomineeCatalog:
    """Concrete :class:`NomineeCatalog` over the Programs and Applications tables."""

    def programs_of(self, competition_id: uuid.UUID, *, organization_id: uuid.UUID) -> Sequence[tuple[uuid.UUID, str]]:
        """The running orders of one festival, as ``(id, name)`` pairs to pick from.

        Scoped through the competition's own organizer so a ballot cannot be seeded
        from another organization's programme by guessing an id.
        """
        if not self._owns(competition_id, organization_id):
            return []
        rows = ProgramModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("name").values_list("id", "name")
        return list(rows)

    def for_program(self, program_id: uuid.UUID, *, organization_id: uuid.UUID) -> Sequence[CatalogNominee]:
        """The performances of one running order, in the order they are performed."""
        program = ProgramModel.objects.filter(pk=program_id, deleted_at__isnull=True).first()
        if program is None or not self._owns(program.competition_id, organization_id):
            return []

        items = list(
            ProgramItemModel.objects.filter(
                program_id=program.id,
                kind=ProgramItemKindChoices.PERFORMANCE,
                deleted_at__isnull=True,
            ).order_by("position")
        )
        submissions = {
            row.id: row
            for row in SubmissionModel.objects.filter(id__in=[item.submission_id for item in items if item.submission_id], deleted_at__isnull=True)
        }

        nominees: list[CatalogNominee] = []
        for item in items:
            submission = submissions.get(item.submission_id) if item.submission_id else None
            title = self._performer(submission, item.title)
            if not title:
                # Nothing to put on a card. Skipped rather than seeded as a blank
                # row the organizer would have to hunt down and fill in.
                continue
            nominees.append(
                CatalogNominee(
                    title=title,
                    subtitle=self._act(submission),
                    # The city is not on a submission; the organizer fills it in if
                    # they want it on the card. Seeding a blank is honest — inventing
                    # one from a related record would be a guess on a public page.
                    city="",
                    number=item.number or None,
                    submission_id=item.submission_id,
                    program_item_id=item.id,
                )
            )
        return nominees

    @staticmethod
    def _owns(competition_id: uuid.UUID | None, organization_id: uuid.UUID) -> bool:
        if competition_id is None:
            return False
        return CompetitionModel.objects.filter(pk=competition_id, organizer_id=organization_id, deleted_at__isnull=True).exists()

    @staticmethod
    def _performer(submission: SubmissionModel | None, fallback: str) -> str:
        """Who is on stage, as the audience would name them.

        The participants, because that is who the hall is voting for. A solo act
        names one person; an ensemble names several and is shortened, since a card
        listing twelve children is a card nobody reads from the back row. When the
        submission names nobody at all the programme row's own title is used —
        which is what a hand-written service row carries.
        """
        if submission is None:
            return fallback
        names = [name for name in (_person(entry) for entry in submission.participants or []) if name]
        if not names:
            return fallback
        if len(names) <= _NAMES_ON_A_CARD:
            return ", ".join(names)
        return f"{names[0]} и ещё {len(names) - 1}"

    @staticmethod
    def _act(submission: SubmissionModel | None) -> str:
        """What they performed — the act's own title."""
        if submission is None:
            return ""
        performance = submission.performance if isinstance(submission.performance, dict) else {}
        title = performance.get("title")
        return title.strip() if isinstance(title, str) else ""
