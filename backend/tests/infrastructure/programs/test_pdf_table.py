"""Tests for the programme PDF renderer - the shapes a real programme takes.

The one that matters is a long comment: an organizer who writes a paragraph about props
and light produces a row taller than a landscape A4, and a table that may only break
between rows has nowhere to break - which used to end the export in a 500 rather than a
PDF. Everything here renders a document and asserts only that bytes came back, because
the failure mode under test is an exception, not a layout detail.
"""

from __future__ import annotations

from apps.programs.application.dto import ColumnView, ProgramTableView
from apps.programs.infrastructure.pdf.table import ReportLabTableRenderer

_KEYS = (
    "number",
    "time",
    "participant",
    "act",
    "duration",
    "nomination",
    "age",
    "organization",
    "contacts",
    "person",
    "comment",
)


def _view(rows: tuple[tuple[str, ...], ...], *, columns: tuple[str, ...] = _KEYS) -> ProgramTableView:
    return ProgramTableView(
        title="Программа фестиваля",
        subtitle="Большая сцена",
        starts_at=None,
        total_seconds=7200,
        columns=tuple(ColumnView(key=key, label=key.capitalize()) for key in columns),
        rows=rows,
    )


def _row(index: int, **overrides: str) -> tuple[str, ...]:
    return tuple(overrides.get(key, f"{key}-{index}") for key in _KEYS)


def test_renders_an_ordinary_programme() -> None:
    assert ReportLabTableRenderer().render(_view((_row(1), _row(2)))).startswith(b"%PDF")


def test_renders_a_comment_taller_than_the_page() -> None:
    """Every column chosen and a comment long enough to outgrow one page on its own."""
    comment = "Нужен реквизит, свет и две минуты на перестановку. " * 40
    assert ReportLabTableRenderer().render(_view((_row(1, comment=comment), _row(2)))).startswith(b"%PDF")


def test_renders_a_comment_spanning_several_pages() -> None:
    assert ReportLabTableRenderer().render(_view((_row(1, comment="Комментарий " * 2000),))).startswith(b"%PDF")


def test_renders_a_word_wider_than_its_column() -> None:
    """A contact pasted without spaces must not push the table off the page."""
    assert ReportLabTableRenderer().render(_view((_row(1, contacts="Ы" * 400),))).startswith(b"%PDF")


def test_renders_without_columns() -> None:
    assert ReportLabTableRenderer().render(_view((), columns=())).startswith(b"%PDF")
