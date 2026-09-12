"""Handing a workbook to the browser.

Mirrors :func:`config.archive.zip_response`: the file is streamed from the spool
the writer produced rather than read into memory to be handed over, and the
download name survives Cyrillic intact — a filename header that is not encoded
reaches the browser as mojibake, and the organizer saves «Ð½Ð¾Ð¼Ð¸Ð½Ð°Ð½Ñ‚Ñ‹.xlsx».
"""

from __future__ import annotations

from typing import IO
from urllib.parse import quote

from django.http import FileResponse

__all__ = ["XLSX_CONTENT_TYPE", "xlsx_response"]

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def xlsx_response(payload: IO[bytes], *, filename: str) -> FileResponse:
    """Stream ``payload`` as an .xlsx download named ``filename``."""
    response = FileResponse(payload, content_type=XLSX_CONTENT_TYPE)
    # Both forms: the plain one for clients that only read it, the RFC 5987 one
    # carrying the real name. A browser that understands `filename*` prefers it.
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii")
    response["Content-Disposition"] = f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"
    return response
