"""The organization's diploma-number format.

A number is ``VT-2026-000001``: the constant organization prefix, the **year of
the competition** (not the system year — a competition held in 2026 keeps 2026 in
its numbers however late the diploma is printed), and a six-digit, zero-padded
sequence.

Pure formatting only — framework-free and side-effect-free. The counter behind
``sequence`` is reserved by the application ``DiplomaNumberService`` through the
:class:`~apps.diplomas.application.interfaces.DiplomaNumberSequence` port, so
changing this format touches this module alone.
"""

from __future__ import annotations

__all__ = ["ORGANIZATION_PREFIX", "SEQUENCE_WIDTH", "format_diploma_number"]

#: Constant organization prefix («Взлёт талантов»).
ORGANIZATION_PREFIX = "VT"

#: Zero-pad width of the per-year sequence (000001, 000002, …).
SEQUENCE_WIDTH = 6


def format_diploma_number(*, year: int, sequence: int) -> str:
    """Render ``VT-<year>-<sequence>``, e.g. ``VT-2026-000001``.

    ``sequence`` is a positive counter value; wider values simply grow past the
    padding rather than being truncated (a number is never ambiguous).
    """
    return f"{ORGANIZATION_PREFIX}-{year:04d}-{sequence:0{SEQUENCE_WIDTH}d}"
