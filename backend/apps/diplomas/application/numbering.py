"""Diploma numbering use case.

One seam owns the whole number: :class:`DiplomaNumberService` reserves the next
counter value through the :class:`DiplomaNumberSequence` port and renders it with
the domain format helper. Nothing else in the system knows what a number looks
like, so the format can change here without touching the registry, the batch
generator or the PDF renderer.

The counter is **scoped by competition year** — the year is part of the number, so
each year has its own ``000001…`` run and the whole number stays unique.
"""

from __future__ import annotations

from apps.diplomas.application.interfaces import DiplomaNumberSequence
from apps.diplomas.domain.diploma_number import format_diploma_number

__all__ = ["DiplomaNumberService"]


class DiplomaNumberService:
    """Mint permanent diploma numbers (``VT-2026-000001``)."""

    def __init__(self, *, sequence: DiplomaNumberSequence) -> None:
        self._sequence = sequence

    def next_number(self, *, competition_year: int) -> str:
        """Reserve and format the next number for a competition year.

        Reserving is a single atomic, row-locked step in the adapter, so parallel
        workers never receive the same value.
        """
        value = self._sequence.next_value(scope=str(competition_year))
        return format_diploma_number(year=competition_year, sequence=value)
