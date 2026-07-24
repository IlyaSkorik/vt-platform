"""Render a diploma PDF: overlay the template's placed fields onto its backing PDF.

Draws each data-bound field's resolved text at its normalised position with the
field's style — honouring font family/weight/style, size, colour, alignment,
auto-shrink and wrapping — then merges the overlay onto the immutable background.
A field that resolves to nothing is skipped (no placeholder), so a print copy
with no degree simply omits the Степень field.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.pdf.field_values import field_text
from apps.diplomas.infrastructure.pdf.fonts import resolve_font

__all__ = ["render_diploma_pdf"]

_MIN_FONT_PT = 4.0


def _color(value: Any) -> HexColor:
    text = str(value or "#000000").strip()
    try:
        return HexColor(text)
    except (ValueError, TypeError):
        return HexColor("#000000")


def _string_width(text: str, font: str, size: float, char_space: float) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    width = stringWidth(text, font, size)
    if char_space and text:
        width += char_space * (len(text) - 1)
    return width


def _wrap(text: str, font: str, size: float, max_width: float, char_space: float) -> list[str]:
    """Greedy word-wrap within ``max_width``; also honours explicit newlines."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and _string_width(candidate, font, size, char_space) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def _fit_size(text: str, font: str, base: float, box_w: float, box_h: float, char_space: float, wrap: bool) -> tuple[float, list[str]]:
    """Shrink the font until the text fits the box; return (size, lines)."""
    size = base
    while size > _MIN_FONT_PT:
        lines = _wrap(text, font, size, box_w, char_space) if wrap else text.split("\n")
        widest = max((_string_width(line, font, size, char_space) for line in lines), default=0.0)
        total_h = len(lines) * size * 1.2
        if widest <= box_w and total_h <= box_h:
            return size, lines
        size -= max(0.5, size * 0.06)
    lines = _wrap(text, font, _MIN_FONT_PT, box_w, char_space) if wrap else text.split("\n")
    return _MIN_FONT_PT, lines


def _draw_field(c: canvas.Canvas, field: dict[str, Any], text: str, page_w: float, page_h: float) -> None:
    style = field.get("style") or {}
    box_x = float(field["x"]) * page_w
    box_top = float(field["y"]) * page_h
    box_w = float(field["width"]) * page_w
    box_h = float(field["height"]) * page_h
    box_bottom = page_h - (box_top + box_h)

    base_size = float(style.get("fontSize", 24) or 24)
    weight = style.get("fontWeight", "normal") == "bold"
    italic = style.get("fontStyle", "normal") == "italic"
    font = resolve_font(str(style.get("fontFamily", "")), bold=weight, italic=italic)
    align = style.get("textAlign", "center")
    line_height = float(style.get("lineHeight", 1.2) or 1.2)
    char_space = float(style.get("letterSpacing", 0) or 0)
    auto_shrink = bool(style.get("autoShrink", True))
    wrap = bool(style.get("wrapText", False))

    if auto_shrink:
        size, lines = _fit_size(text, font, base_size, box_w, box_h, char_space, wrap)
    else:
        size = base_size
        lines = _wrap(text, font, size, box_w, char_space) if wrap else text.split("\n")

    c.setFont(font, size)
    c.setFillColor(_color(style.get("color")))
    if char_space:
        c.setCharSpace(char_space)

    step = size * line_height
    block_h = step * len(lines)
    # Vertically centre the block within the box.
    top_baseline = box_bottom + (box_h + block_h) / 2 - size
    for index, line in enumerate(lines):
        y = top_baseline - index * step
        if align == "left":
            c.drawString(box_x, y, line)
        elif align == "right":
            c.drawRightString(box_x + box_w, y, line)
        else:
            c.drawCentredString(box_x + box_w / 2, y, line)
    if char_space:
        c.setCharSpace(0)


def _overlay(fields: list[dict[str, Any]], snapshot: DiplomaSnapshot, number: str, w: float, h: float) -> bytes | None:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(w, h))
    drew = False
    for field in fields:
        text = field_text(field, snapshot, number=number)
        if not text:
            continue
        drew = True
        _draw_field(c, field, text, w, h)
    if not drew:
        return None
    c.save()
    return buffer.getvalue()


def render_diploma_pdf(
    *, fields: list[dict[str, Any]], backing_pdf: bytes, snapshot: DiplomaSnapshot, number: str
) -> bytes:
    """Produce the diploma PDF bytes: the backing PDF with the fields overlaid."""
    # Clone into the writer first so pages are writer-attached before merging the
    # overlay (the reliable pypdf path).
    writer = PdfWriter(clone_from=PdfReader(BytesIO(backing_pdf)))
    for index, page in enumerate(writer.pages, start=1):
        page_fields = [f for f in fields if int(f.get("page", 1)) == index]
        if not page_fields:
            continue
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay = _overlay(page_fields, snapshot, number, width, height)
        if overlay is not None:
            page.merge_page(PdfReader(BytesIO(overlay)).pages[0])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
