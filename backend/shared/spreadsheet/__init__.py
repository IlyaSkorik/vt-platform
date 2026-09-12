"""Reading and writing the spreadsheets organizers actually work in.

A technical helper, not a bounded context: it knows about the xlsx format and
about HTTP, and nothing about festivals, nominees or diplomas. It sits beside
:mod:`config.archive` in spirit — several edges need the same thing and none of
them should own the others' copy of it.

**xlsx and not CSV.** The people on the other end of this open files in Excel, and
CSV loses the encoding argument with a Russian Excel every time: a file this
platform writes correctly is opened as mojibake, and a file they save comes back
in whatever their locale felt like. The format that survives the round trip is
the one they already use.

Three modules:

* :mod:`.reader` — a submitted workbook to rows, tolerantly.
* :mod:`.writer` — rows to a workbook, safely.
* :mod:`.http` — a workbook to a download.
"""

from __future__ import annotations

from .http import xlsx_response
from .reader import (
    MAX_COLUMNS,
    MAX_ROWS,
    MAX_UPLOAD_BYTES,
    Column,
    RowError,
    SheetReadError,
    SheetRows,
    read_rows,
)
from .writer import Cell, SheetColumn, write_workbook

__all__ = [
    "MAX_COLUMNS",
    "MAX_ROWS",
    "MAX_UPLOAD_BYTES",
    "Cell",
    "Column",
    "RowError",
    "SheetColumn",
    "SheetReadError",
    "SheetRows",
    "read_rows",
    "write_workbook",
    "xlsx_response",
]
