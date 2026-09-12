"""The nominee list as a spreadsheet: the template, the import and the results.

Three things, all built on :mod:`shared.spreadsheet` so this context owns no xlsx
knowledge of its own.

**The template matters as much as the import.** An import with no example file
does not work in practice: the organizer sends the table they already have, in
their own shape, and comes back with a question. Handing them a file with the
right headings and a filled-in example row turns that around — they send our file
with their data in it.

The columns are matched by name and by synonym, so a list exported from another
system with «ФИО» instead of «Участник», or with the columns in a different order,
still reads correctly.
"""

from __future__ import annotations

from typing import IO, Final

from apps.voting.application.commands import NomineeRow
from apps.voting.application.dto import BallotDetailView
from shared.spreadsheet import Column, SheetColumn, SheetRows, read_rows, write_workbook

__all__ = ["NOMINEE_COLUMNS", "read_nominees", "results_workbook", "template_workbook"]

#: What a nominee list may call its columns.
#:
#: The first name of each is the heading the template offers; the rest are what a
#: file from somewhere else is likely to say. Only the performer is required — a
#: list with nothing but names is a perfectly good ballot.
NOMINEE_COLUMNS: Final = (
    Column(key="number", names=("Номер", "№", "Номер выступления")),
    Column(key="title", names=("Участник", "ФИО", "Коллектив", "Исполнитель"), required=True),
    Column(key="subtitle", names=("Произведение", "Номер программы", "Название номера", "Репертуар")),
    Column(key="city", names=("Город", "Населённый пункт", "Населенный пункт")),
)

#: One row of the template, so the format is shown rather than described.
_EXAMPLE_ROW: Final = ("1", "Ансамбль «Ритм»", "«Калинка»", "Минск")


def template_workbook() -> IO[bytes]:
    """The empty list, with its headings and one example row."""
    return write_workbook(
        columns=[SheetColumn(heading=column.heading) for column in NOMINEE_COLUMNS],
        rows=[_EXAMPLE_ROW],
        sheet_title="Номинанты",
    )


def read_nominees(source: IO[bytes]) -> tuple[tuple[NomineeRow, ...], SheetRows]:
    """Read a submitted file into nominee rows, keeping what could not be used.

    The rejected rows travel back with the good ones so the preview can show them
    together — an organizer fixing line 14 should not have to look for it in a
    different part of the screen from the lines that worked.
    """
    sheet = read_rows(source, columns=NOMINEE_COLUMNS)
    rows = tuple(
        NomineeRow(
            title=row.get("title", ""),
            subtitle=row.get("subtitle", ""),
            city=row.get("city", ""),
            number=_as_number(row.get("number", "")),
        )
        for row in sheet.rows
    )
    return rows, sheet


def results_workbook(ballot: BallotDetailView) -> IO[bytes]:
    """The finished vote, in the order it finished in.

    Sorted by votes rather than by the running order: a results file is read to
    find out who won, and making the reader sort it themselves is making them do
    the one thing they opened it for. Withdrawn nominees stay in the table with the
    votes they had — a result that quietly loses a contestant cannot be audited.
    """
    ranked = sorted(ballot.nominees, key=lambda nominee: (-nominee.votes, nominee.position))
    rows = [
        (
            place,
            nominee.number,
            nominee.title,
            nominee.subtitle,
            nominee.city,
            nominee.votes,
            "снят" if nominee.withdrawn else "",
        )
        for place, nominee in enumerate(ranked, start=1)
    ]
    return write_workbook(
        columns=[
            SheetColumn(heading="Место", width=10),
            SheetColumn(heading="Номер", width=10),
            SheetColumn(heading="Участник"),
            SheetColumn(heading="Произведение"),
            SheetColumn(heading="Город"),
            SheetColumn(heading="Голосов", width=12),
            SheetColumn(heading="Примечание", width=14),
        ],
        rows=rows,
        sheet_title="Итоги голосования",
    )


def _as_number(text: str) -> int | None:
    """A performance number, or ``None`` when the cell held something else.

    Deliberately forgiving: the number is decoration on a card, and refusing a
    whole row because somebody wrote "1а" would be refusing a nominee over a label.
    """
    digits = "".join(character for character in text if character.isdigit())
    return int(digits) if digits else None
