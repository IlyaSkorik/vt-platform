"""``ReportLabTableRenderer`` - prints a rendered table as a PDF the organizer can hand out.

A dumb table printer: it is given a heading, column headers and rows of text, and knows
nothing about programmes. Every decision about *what* a cell says was already made in the
application layer, which is what keeps an exported table and a screen in agreement.

Two things make this readable rather than merely correct. It is **landscape** with columns
sized to their own content, because a programme table is wide and a narrow column of times
next to a wide column of names is what a person actually scans. And the header row
**repeats on every page**, because a running order rarely fits on one and a second page of
unlabelled columns is useless at the side of a stage.

Cyrillic needs a Unicode TrueType font registered with reportlab; DejaVu is bundled for
exactly that reason.
"""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.programs.application.dto import ProgramTableView

__all__ = ["ReportLabTableRenderer"]

#: Where to look for the Unicode TrueType font Cyrillic needs. This context's own directory
#: first, so an operator can drop a family here; the platform's bundled DejaVu after it.
_FONT_DIRS = (
    Path(__file__).resolve().parent / "fonts",
    Path(__file__).resolve().parents[3] / "diplomas" / "infrastructure" / "pdf" / "fonts",
)
#: Registered under names of this context's own, so two contexts registering the same file
#: cannot interfere with each other.
_REGULAR = "ProgramsDejaVuSans"
_BOLD = "ProgramsDejaVuSans-Bold"
_registered = False


def _register_fonts() -> tuple[str, str]:
    """Register the bundled font once; fall back to Helvetica if none is found.

    Helvetica cannot draw Cyrillic, so that fallback is a legible failure rather than a
    correct one - but an export that comes out wrong beats an export that raises.
    """
    global _registered
    if _registered:
        return _REGULAR, _BOLD
    for directory in _FONT_DIRS:
        regular, bold = directory / "DejaVuSans.ttf", directory / "DejaVuSans-Bold.ttf"
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont(_REGULAR, str(regular)))
            pdfmetrics.registerFont(TTFont(_BOLD, str(bold)))
            _registered = True
            return _REGULAR, _BOLD
    return "Helvetica", "Helvetica-Bold"


class ReportLabTableRenderer:
    """Concrete :class:`~apps.programs.application.interfaces.TableRenderer` (PDF)."""

    #: Room for the page margins on a landscape A4.
    _MARGIN = 12 * mm
    #: No column narrower than this, so a one-character header still reads as a column.
    _MIN_COLUMN = 14 * mm

    def render(self, table: ProgramTableView) -> bytes:
        regular, bold = _register_fonts()
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=self._MARGIN,
            rightMargin=self._MARGIN,
            topMargin=self._MARGIN,
            bottomMargin=self._MARGIN,
            title=table.title,
        )
        available = document.width

        heading_style = ParagraphStyle("heading", fontName=bold, fontSize=15, leading=19, alignment=TA_LEFT)
        sub_style = ParagraphStyle("sub", fontName=regular, fontSize=9, leading=12, textColor=colors.HexColor("#555555"))
        cell_style = ParagraphStyle("cell", fontName=regular, fontSize=8, leading=10)
        header_style = ParagraphStyle("header", fontName=bold, fontSize=8, leading=10, textColor=colors.white)

        story: list[object] = [
            KeepTogether(
                [
                    Paragraph(table.title, heading_style),
                    *([Paragraph(table.subtitle, sub_style)] if table.subtitle else []),
                    Paragraph(self._summary(table), sub_style),
                    Spacer(1, 5 * mm),
                ]
            )
        ]

        if not table.columns:
            story.append(Paragraph("Не выбрано ни одной колонки.", cell_style))
        else:
            header = [Paragraph(column.label, header_style) for column in table.columns]
            body = [[Paragraph(cell or "—", cell_style) for cell in row] for row in table.rows]
            grid = Table(
                [header, *body],
                colWidths=self._column_widths(table, available),
                repeatRows=1,
                hAlign="LEFT",
            )
            grid.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        # Banded rows: on a wide table they are what keeps the eye on one line.
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                    ]
                )
            )
            story.append(grid)

        document.build(story)
        return buffer.getvalue()

    @staticmethod
    def _summary(table: ProgramTableView) -> str:
        parts = [f"Пунктов: {len(table.rows)}"]
        hours, remainder = divmod(max(0, table.total_seconds), 3600)
        minutes = remainder // 60
        parts.append(f"Продолжительность: {hours} ч {minutes:02d} мин" if hours else f"Продолжительность: {minutes} мин")
        if table.starts_at is not None:
            parts.append(f"Начало: {table.starts_at.strftime('%H:%M')}")
        return " · ".join(parts)

    def _column_widths(self, table: ProgramTableView, available: float) -> list[float]:
        """Share the page between columns in proportion to what they actually hold.

        Measuring the content beats fixed weights per column: a programme where every act
        has a long comment wants a different split from one where none do, and the
        organizer chooses the columns anyway.
        """
        count = len(table.columns)
        demands: list[float] = []
        for index, column in enumerate(table.columns):
            longest = max(
                (len(row[index]) for row in table.rows if index < len(row)),
                default=0,
            )
            # A header is bold and a little wider per character; +2 is its padding.
            demands.append(float(max(len(column.label) + 2, min(longest, 60))))
        total = sum(demands) or float(count)
        floor = min(self._MIN_COLUMN, available / count)
        flexible = max(available - floor * count, 0.0)
        return [floor + flexible * (demand / total) for demand in demands]
