"""``DjangoRunningOrderSource`` - reads the Programs context, and only reads it.

A protocol opens in the order the acts performed, with the numbers they were announced
under, because that is the list the jury had in front of them from the hall. This adapter
is where that order comes from: the nomination's programmes, their performance slots, in
position order.

Strictly one-directional. Programs never learns that Results exists, nothing here writes,
and the order is **copied once** at seeding rather than joined on every read - a programme
rearranged for a second stage, or deleted after the festival, must not move a result that
has already been awarded.

Blocks are skipped: a break, an opening or an award ceremony occupies a slot in a running
order and can never carry a result, so it never reaches this context at all.
"""

from __future__ import annotations

import uuid

from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel
from apps.programs.infrastructure.models.program import ProgramItemKindChoices
from apps.results.application.interfaces import RunningOrderEntry

__all__ = ["DjangoRunningOrderSource"]


class DjangoRunningOrderSource:
    """Concrete :class:`~apps.results.application.interfaces.RunningOrderSource`."""

    def running_order(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> tuple[RunningOrderEntry, ...]:
        """This nomination's performance slots, in the order they were scheduled to run.

        A nomination split across several programmes ("Вокал, 1 отделение" and "2
        отделение") reads as one sequence, oldest programme first: the protocol is the
        nomination's, not one session's.

        The first occurrence of an act wins if it somehow appears in two programmes - a
        protocol has one row per act, and the number it was first announced under is the
        one participants were told.
        """
        program_ids = list(self._program_ids(competition_id=competition_id, nomination_id=nomination_id))
        if not program_ids:
            return ()
        rows = (
            ProgramItemModel.objects.filter(
                program_id__in=program_ids,
                kind=ProgramItemKindChoices.PERFORMANCE,
                submission_id__isnull=False,
                deleted_at__isnull=True,
            )
            .order_by("program__created_at", "position")
            .values_list("submission_id", "number", "position")
        )
        entries: list[RunningOrderEntry] = []
        seen: set[uuid.UUID] = set()
        for submission_id, number, position in rows:
            # The query already excludes null submissions; the guard is what tells the type
            # checker so, and it costs nothing to be right if that filter is ever relaxed.
            if submission_id is None or submission_id in seen:
                continue
            seen.add(submission_id)
            entries.append(RunningOrderEntry(submission_id=submission_id, number=int(number) or int(position)))
        return tuple(entries)

    def program_id_for(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> uuid.UUID | None:
        """The programme the order came from - the oldest, when there are several.

        Recorded on the protocol as provenance ("собран из программы"), not as a link the
        protocol reads through later. With several programmes it names the first, which is
        the one an organizer thinks of as *the* programme of that nomination.
        """
        return next(iter(self._program_ids(competition_id=competition_id, nomination_id=nomination_id)), None)

    @staticmethod
    def _program_ids(*, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        """This nomination's live programmes, oldest first.

        Includes the competition's nomination-less programmes as a fallback: an organizer
        who ran a single programme for the whole festival still expects a protocol to open
        in performance order. Rows for other nominations are filtered out downstream by
        the catalog, which is the module that knows which acts belong to this nomination.
        """
        rows = ProgramModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("created_at")
        scoped = tuple(rows.filter(nomination_id=nomination_id).values_list("id", flat=True))
        if scoped:
            return scoped
        return tuple(rows.filter(nomination_id__isnull=True).values_list("id", flat=True))
