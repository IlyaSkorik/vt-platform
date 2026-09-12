"""Turning a workbook somebody sent us into rows we can trust.

The file on the other end of this was not produced by us. It was exported from a
different system, or typed by hand over three evenings, and it will have the
columns in a different order, a merged title across the top, formulas where you
expected text, and a hundred blank rows at the bottom where somebody once pressed
delete. Reading it *tolerantly* is the whole job; a reader that only accepts the
file we would have written ourselves is a reader nobody can use.

What it does about each of those:

* **Column order.** Columns are matched by name, case- and space-insensitively,
  through the synonyms each caller declares. Position is never assumed.
* **A header that is not the first row.** The header is looked for among the first
  :data:`HEADER_SEARCH_ROWS` rows — the one that matches the most declared columns
  wins. A report with a merged title above the table reads correctly.
* **Formulas.** Read with ``data_only``, so a cell holding ``=A1&" "&B1`` yields the
  text Excel last computed rather than the formula's source.
* **Size.** Refused before parsing, by bytes and by row count. A workbook with a
  million rows is a denial of service with a friendly file extension.
* **Blank rows.** Skipped rather than reported as errors — trailing emptiness is
  how spreadsheets are, not something the organizer did wrong.

Errors are per row and carry the row's number *as Excel shows it*, because that is
the number the person will look for when they go and fix it.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import IO, Any, Final

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

__all__ = [
    "HEADER_SEARCH_ROWS",
    "MAX_COLUMNS",
    "MAX_ROWS",
    "MAX_UPLOAD_BYTES",
    "Column",
    "RowError",
    "SheetReadError",
    "SheetRows",
    "read_rows",
]

#: How far down the sheet the header is looked for before giving up.
HEADER_SEARCH_ROWS: Final = 10

#: Ceilings applied before the workbook is parsed at all.
#:
#: Generous for a real list — a festival's nominee list is tens of rows and its
#: participant registry is thousands — and far below what it takes to exhaust a
#: worker. The point is that an accidental or hostile file is refused by the
#: guard rather than by the OOM killer.
MAX_UPLOAD_BYTES: Final = 8 * 1024 * 1024
MAX_ROWS: Final = 20_000
MAX_COLUMNS: Final = 64


class SheetReadError(Exception):
    """The workbook could not be read at all (as opposed to one bad row).

    Carries a message written for the person who uploaded the file — this is
    rendered straight into the interface.
    """


@dataclass(frozen=True, slots=True)
class Column:
    """One column the caller expects, and the names it might arrive under.

    ``key`` is how the caller refers to the value afterwards; ``names`` are the
    headings a real file might use for it. The first name doubles as the heading
    written into the template the caller hands out, so it should be the one they
    would like to receive.
    """

    key: str
    names: tuple[str, ...]
    required: bool = False

    @property
    def heading(self) -> str:
        """The preferred heading — what the template offers."""
        return self.names[0]


@dataclass(frozen=True, slots=True)
class RowError:
    """One row that could not be used, and why — addressed to the person, by row."""

    #: The row number as Excel displays it, so it can actually be found and fixed.
    row: int
    message: str


@dataclass(frozen=True, slots=True)
class SheetRows:
    """The outcome of reading a sheet: what came through, and what did not."""

    rows: tuple[dict[str, str], ...] = ()
    errors: tuple[RowError, ...] = ()
    #: Columns the caller declared that this file simply does not have. Reported so
    #: the interface can say "we ignored these" instead of silently dropping them.
    missing_columns: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """Whether every row came through."""
        return not self.errors


def _normalize(value: object) -> str:
    """Fold a heading or a cell into its comparable form."""
    return " ".join(str(value).split()).strip().lower() if value is not None else ""


def _cell_text(value: object) -> str:
    """Render a cell as the text a person would say is in it.

    Whole floats lose the decimal tail Excel invents for them: a participant number
    typed as ``12`` arrives as ``12.0`` and must not be written down that way.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split()).strip()


def _ensure_xlsx(source: IO[bytes]) -> None:
    """Refuse anything that is not really a workbook, by content and by size.

    The extension and the ``Content-Type`` are both supplied by the caller and
    neither is evidence. An xlsx is a zip container; if it does not open as one it
    is not a workbook whatever it is named — the same reasoning that makes uploaded
    images go through Pillow rather than through their file name.
    """
    source.seek(0, 2)
    size = source.tell()
    source.seek(0)
    if size == 0:
        raise SheetReadError("Файл пустой.")
    if size > MAX_UPLOAD_BYTES:
        megabytes = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise SheetReadError(f"Файл больше {megabytes} МБ. Загрузите таблицу поменьше.")
    if not zipfile.is_zipfile(source):
        raise SheetReadError("Это не файл Excel (.xlsx). Сохраните таблицу в формате «Книга Excel» и попробуйте снова.")
    source.seek(0)


def _header_row(grid: Sequence[Sequence[Any]], columns: Sequence[Column]) -> tuple[int, dict[int, str]]:
    """Find the header among the first rows, and map its positions to column keys.

    The best candidate wins rather than the first: a sheet whose first row holds a
    merged title matches nothing, and the real header two rows down matches
    everything. A tie goes to the higher row, which is the one a person would call
    the header.
    """
    lookup = {_normalize(name): column.key for column in columns for name in column.names}

    best_index = -1
    best_mapping: dict[int, str] = {}
    for index, row in enumerate(grid[:HEADER_SEARCH_ROWS]):
        mapping = {position: lookup[text] for position, cell in enumerate(row) if (text := _normalize(cell)) in lookup}
        if len(mapping) > len(best_mapping):
            best_index, best_mapping = index, mapping

    if not best_mapping:
        expected = ", ".join(f"«{column.heading}»" for column in columns if column.required) or ", ".join(f"«{column.heading}»" for column in columns)
        raise SheetReadError(f"Не нашли строку заголовков. Ожидаем колонки: {expected}. Скачайте шаблон и заполните его.")

    return best_index, best_mapping


def read_rows(source: IO[bytes], *, columns: Sequence[Column]) -> SheetRows:
    """Read the first sheet of ``source`` into rows keyed by :attr:`Column.key`.

    Every value comes back as trimmed text. Typing it is the caller's business —
    this module has no opinion about what a "number" or a "date" means in their
    domain, and guessing would produce a second place where that is decided.
    """
    _ensure_xlsx(source)

    try:
        workbook = load_workbook(source, read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise SheetReadError("Не удалось прочитать файл Excel. Возможно, он повреждён.") from exc

    try:
        sheet = workbook.worksheets[0] if workbook.worksheets else None
        if sheet is None:
            raise SheetReadError("В файле нет ни одного листа.")
        grid = list(_bounded_grid(sheet.iter_rows(values_only=True)))
    finally:
        workbook.close()

    if not grid:
        raise SheetReadError("Лист пустой.")

    header_index, mapping = _header_row(grid, columns)
    present = set(mapping.values())
    missing = tuple(column.heading for column in columns if column.key not in present)
    required_missing = [column.heading for column in columns if column.required and column.key not in present]
    if required_missing:
        raise SheetReadError("В таблице нет обязательных колонок: " + ", ".join(f"«{name}»" for name in required_missing) + ".")

    rows: list[dict[str, str]] = []
    errors: list[RowError] = []
    for offset, raw in enumerate(grid[header_index + 1 :], start=header_index + 2):
        values = {key: _cell_text(raw[position]) if position < len(raw) else "" for position, key in mapping.items()}
        # A row with nothing in any column we care about is the empty tail of the
        # sheet, not a mistake. Reporting it would bury the real errors.
        if not any(values.values()):
            continue
        blank_required = [column.heading for column in columns if column.required and not values.get(column.key)]
        if blank_required:
            errors.append(RowError(row=offset, message="Не заполнено: " + ", ".join(f"«{name}»" for name in blank_required) + "."))
            continue
        rows.append(values)

    return SheetRows(rows=tuple(rows), errors=tuple(errors), missing_columns=missing)


def _bounded_grid(source: Iterable[tuple[Any, ...]]) -> Iterator[tuple[Any, ...]]:
    """Yield rows up to the ceilings, refusing a file that runs past them.

    Checked while streaming rather than from the sheet's declared dimensions: those
    are written by whatever produced the file and a hostile one can lie about them.
    """
    for count, row in enumerate(source, start=1):
        if count > MAX_ROWS:
            raise SheetReadError(f"В таблице больше {MAX_ROWS} строк. Разбейте её на части.")
        yield row[:MAX_COLUMNS]
