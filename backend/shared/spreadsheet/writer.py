"""Building the workbook we hand back.

Two jobs beyond "put values in cells":

**Formulas do not leave this building.** A value that begins with ``=``, ``+``,
``-`` or ``@`` is written as text. Excel treats such a cell as a formula, so an
export of data we did not author — a participant's name, a nominee's title, a note
typed into a form — would become code that runs on the recipient's machine when
they open the file. The export is a report, and a report must not execute.

**It streams.** The workbook is built in ``write_only`` mode, so a registry of
several thousand rows is written as it is produced rather than assembled whole in
memory and then serialized (which holds it twice).

Column widths are measured from the headings and a sample of the rows. A table
whose every column is the default width is one the recipient has to resize before
they can read it, and they will not thank us for that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from typing import IO, Final

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

__all__ = ["Cell", "SheetColumn", "write_workbook"]

#: A value starting with any of these is a formula to Excel. See the module docstring.
_FORMULA_LEADERS: Final = ("=", "+", "-", "@")

#: Width bounds, in Excel's character units.
_MIN_WIDTH: Final = 10
_MAX_WIDTH: Final = 60

#: How many rows are measured before the widths are fixed. Enough to be
#: representative; bounded so a large export does not pay for perfect columns.
_WIDTH_SAMPLE_ROWS: Final = 200

#: How much of a workbook is held in memory before the spool rolls over to disk
#: (mirrors :mod:`config.archive`).
_SPOOL_BYTES: Final = 4 * 1024 * 1024

#: Excel refuses these in a sheet name.
_SHEET_NAME_FORBIDDEN: Final = set(r"[]:*?/\ ".rstrip())

Cell = str | int | float | None


@dataclass(frozen=True, slots=True)
class SheetColumn:
    """One column of the sheet being written: its heading and its width."""

    heading: str
    #: Overrides the measured width when the caller knows better — a notes column
    #: that should be wide even though this particular export's notes are short.
    width: int | None = None


def _safe(value: Cell) -> Cell:
    """Render a value so Excel treats it as data.

    Numbers pass through as numbers: they are ours, they sort and sum, and a number
    cannot be a formula. Text that looks like one is prefixed with an apostrophe,
    which is how a spreadsheet spells "this is literally text" — Excel consumes the
    mark and displays the value as written.
    """
    if value is None or isinstance(value, (int, float)):
        return value
    text = str(value)
    return f"'{text}" if text.startswith(_FORMULA_LEADERS) else text


def _measure(heading: str, samples: Sequence[Cell]) -> int:
    longest = max((len(str(sample)) for sample in samples if sample is not None), default=0)
    return max(_MIN_WIDTH, min(_MAX_WIDTH, max(len(heading), longest) + 2))


def _sheet_name(title: str) -> str:
    cleaned = "".join(character for character in title if character not in _SHEET_NAME_FORBIDDEN)
    return cleaned[:31] or "Лист1"


def write_workbook(
    *,
    columns: Sequence[SheetColumn],
    rows: Iterable[Sequence[Cell]],
    sheet_title: str = "Лист1",
) -> IO[bytes]:
    """Write one sheet and return the file, rewound and ready to be sent.

    ``rows`` may be any iterable, including a generator over a queryset — it is
    consumed once. The widths are measured from the first
    :data:`_WIDTH_SAMPLE_ROWS` rows, which are held briefly and then written like
    every other row; nothing else is buffered.
    """
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title=_sheet_name(sheet_title))

    iterator = iter(rows)
    sample = [tuple(row) for _, row in zip(range(_WIDTH_SAMPLE_ROWS), iterator, strict=False)]

    for index, column in enumerate(columns):
        width = column.width or _measure(column.heading, [row[index] if index < len(row) else None for row in sample])
        sheet.column_dimensions[get_column_letter(index + 1)].width = width

    # Declared before the first row goes out: a write-only sheet captures its own
    # properties when writing begins, and an assignment made afterwards is silently
    # dropped. The header stays on screen while the recipient scrolls a long list —
    # the one piece of spreadsheet etiquette that decides whether a table is usable.
    sheet.freeze_panes = "A2"

    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="EEF2F7")
    header = []
    for column in columns:
        cell = WriteOnlyCell(sheet, value=column.heading)
        cell.font = header_font
        cell.fill = header_fill
        header.append(cell)
    sheet.append(header)

    for sampled in sample:
        sheet.append([_safe(value) for value in sampled])
    for remaining in iterator:
        sheet.append([_safe(value) for value in remaining])

    # Not a context manager on purpose: the spool has to outlive this function. The
    # response streams from it and closes it when the last byte has gone out — the
    # same arrangement `config.archive` makes for a ZIP.
    spool: IO[bytes] = SpooledTemporaryFile(max_size=_SPOOL_BYTES)  # noqa: SIM115
    workbook.save(spool)
    workbook.close()
    spool.seek(0)
    return spool
