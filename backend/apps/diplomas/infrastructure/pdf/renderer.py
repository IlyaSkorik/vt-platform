"""Render a diploma PDF: overlay the template's placed fields onto its backing PDF.

Draws each data-bound field's resolved text at its normalised position with the
field's style — honouring font family/weight/style, size, colour, alignment,
auto-shrink and wrapping — then merges the overlay onto the immutable background.
A field that resolves to nothing is skipped (no placeholder), so a print copy
with no degree simply omits the Степень field.

A ``qr_block`` field is the one composite: it draws the diploma's QR code (the
verification link) plus a three-line caption beside it — the authenticity
headline, the diploma number, and the host to check it on. A template without the
block simply gets no QR — nothing else changes.

:func:`render_place_sheet_pdf` is the same drawing code with the background left
out: a blank sheet carrying nothing but the degree, where the template places it.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.parse import urlsplit

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.pdf.field_values import field_text
from apps.diplomas.infrastructure.pdf.fonts import resolve_font
from apps.diplomas.infrastructure.pdf.qr import qr_png

__all__ = ["QR_HEADLINE", "qr_caption_lines", "render_diploma_pdf", "render_place_sheet_pdf"]

#: The element a place sheet draws, and the only one it draws.
_DEGREE_FIELD_TYPE = "award_degree"

_MIN_FONT_PT = 4.0

#: First caption line beside the QR code. Mirrors the constructor's ``QR_HEADLINE``
#: so the editor preview and the print match exactly.
QR_HEADLINE = "Подлинность гарантирована!"

#: Lead-in of the third caption line; the host follows.
_QR_VERIFY_PREFIX = "Проверить на"

#: Share of the QR side left as the gap between the code and its caption.
_QR_GAP_RATIO = 0.12


def _display_host(url: str) -> str:
    """The bare host of a verification URL, as printed (no scheme, no ``www.``).

    Taken from the URL the QR encodes, so the printed address and the scanned one
    can never disagree — and the configured domain stays the single source."""
    split = urlsplit(url)
    # A value with no scheme parses as a path; treat its first segment as the host.
    host = split.netloc or split.path.lstrip("/").split("/")[0]
    return host.removeprefix("www.")


def qr_caption_lines(*, number: str, verification_url: str | None) -> list[str]:
    """The QR block's caption, one string per printed line.

    Three lines: the authenticity headline, the diploma number, and where to check
    it. A line whose value is unknown is dropped rather than printed empty.
    """
    lines = [QR_HEADLINE]
    if number:
        lines.append(f"№{number}")
    host = _display_host(verification_url) if verification_url else ""
    if host:
        lines.append(f"{_QR_VERIFY_PREFIX} {host}")
    return lines


def _color(value: Any) -> HexColor:
    text = str(value or "#000000").strip()
    try:
        return HexColor(text)
    except (ValueError, TypeError):
        return HexColor("#000000")


def _string_width(text: str, font: str, size: float, char_space: float) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    # reportlab ships no stubs (mypy.ini), so `stringWidth` is untyped; converting at
    # the boundary keeps that Any from leaking into the layout maths downstream.
    width = float(stringWidth(text, font, size))
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


def _box(field: dict[str, Any], page_w: float, page_h: float) -> tuple[float, float, float, float]:
    """The field's box in PDF points as ``(x, bottom, width, height)``.

    Field geometry is normalised and top-anchored (as in the editor); PDF space is
    bottom-anchored, hence the flip."""
    box_x = float(field["x"]) * page_w
    box_top = float(field["y"]) * page_h
    box_w = float(field["width"]) * page_w
    box_h = float(field["height"]) * page_h
    return box_x, page_h - (box_top + box_h), box_w, box_h


def _draw_lines(
    c: canvas.Canvas,
    lines: list[str],
    *,
    x: float,
    bottom: float,
    width: float,
    height: float,
    size: float,
    line_height: float,
    align: str,
) -> None:
    """Draw a vertically centred block of lines inside a box."""
    step = size * line_height
    top_baseline = bottom + (height + step * len(lines)) / 2 - size
    for index, line in enumerate(lines):
        y = top_baseline - index * step
        if align == "left":
            c.drawString(x, y, line)
        elif align == "right":
            c.drawRightString(x + width, y, line)
        else:
            c.drawCentredString(x + width / 2, y, line)


def _draw_field(c: canvas.Canvas, field: dict[str, Any], text: str, page_w: float, page_h: float) -> None:
    style = field.get("style") or {}
    box_x, box_bottom, box_w, box_h = _box(field, page_w, page_h)

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

    _draw_lines(
        c,
        lines,
        x=box_x,
        bottom=box_bottom,
        width=box_w,
        height=box_h,
        size=size,
        line_height=line_height,
        align=align,
    )
    if char_space:
        c.setCharSpace(0)


def _draw_qr_block(
    c: canvas.Canvas,
    field: dict[str, Any],
    *,
    number: str,
    verification_url: str | None,
    page_w: float,
    page_h: float,
) -> None:
    """Draw the QR block: the code, then its three-line caption.

    The code is a square anchored to the left edge of the block and as tall as the
    block allows; the caption takes the width that is left. With no verification
    URL (no token to encode) only the caption is drawn.
    """
    style = field.get("style") or {}
    box_x, box_bottom, box_w, box_h = _box(field, page_w, page_h)

    qr_side = min(box_h, box_w) if verification_url else 0.0
    gap = qr_side * _QR_GAP_RATIO
    if qr_side:
        c.drawImage(
            ImageReader(BytesIO(qr_png(verification_url or ""))),
            box_x,
            box_bottom + (box_h - qr_side) / 2,
            width=qr_side,
            height=qr_side,
            mask="auto",
        )

    text_x = box_x + qr_side + gap
    text_w = box_w - qr_side - gap
    if text_w <= 0:
        # The block is too narrow for a caption — the code alone still verifies.
        return

    base_size = float(style.get("fontSize", 24) or 24)
    weight = style.get("fontWeight", "normal") == "bold"
    italic = style.get("fontStyle", "normal") == "italic"
    font = resolve_font(str(style.get("fontFamily", "")), bold=weight, italic=italic)
    line_height = float(style.get("lineHeight", 1.2) or 1.2)
    align = style.get("textAlign", "left")

    # The caption is exactly its three lines — it shrinks to fit rather than
    # re-wrapping, so the number never breaks across lines.
    caption = "\n".join(qr_caption_lines(number=number, verification_url=verification_url))
    size, lines = _fit_size(caption, font, base_size, text_w, box_h, 0.0, False)

    c.setFont(font, size)
    c.setFillColor(_color(style.get("color")))
    _draw_lines(
        c,
        lines,
        x=text_x,
        bottom=box_bottom,
        width=text_w,
        height=box_h,
        size=size,
        line_height=line_height,
        align=align,
    )


def _overlay(
    fields: list[dict[str, Any]],
    snapshot: DiplomaSnapshot,
    number: str,
    verification_url: str | None,
    w: float,
    h: float,
) -> bytes | None:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(w, h))
    drew = False
    for field in fields:
        if field.get("type") == "qr_block":
            _draw_qr_block(
                c,
                field,
                number=number,
                verification_url=verification_url,
                page_w=w,
                page_h=h,
            )
            drew = True
            continue
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
    *,
    fields: list[dict[str, Any]],
    backing_pdf: bytes,
    snapshot: DiplomaSnapshot,
    number: str,
    verification_url: str | None = None,
) -> bytes:
    """Produce the diploma PDF bytes: the backing PDF with the fields overlaid.

    ``verification_url`` is what a ``qr_block`` field encodes into its QR code;
    without it the block prints its caption only."""
    # Clone into the writer first so pages are writer-attached before merging the
    # overlay (the reliable pypdf path).
    writer = PdfWriter(clone_from=PdfReader(BytesIO(backing_pdf)))
    for index, page in enumerate(writer.pages, start=1):
        page_fields = [f for f in fields if int(f.get("page", 1)) == index]
        if not page_fields:
            continue
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay = _overlay(page_fields, snapshot, number, verification_url, width, height)
        if overlay is not None:
            page.merge_page(PdfReader(BytesIO(overlay)).pages[0])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def render_place_sheet_pdf(*, fields: list[dict[str, Any]], backing_pdf: bytes, degree: str) -> bytes | None:
    """A blank sheet carrying only ``degree``, exactly where the template places it.

    The print package is produced before the ceremony, so its diplomas leave the
    Степень field empty — the jury has not decided yet. Afterwards the awarded
    degree has to reach a sheet that is already printed, and the only way to put it
    there is to feed that sheet back through the printer with a page that is blank
    apart from the degree. This renders that page: same page count and page sizes as
    the template's backing PDF, the degree drawn with the field's own position,
    font, size, colour and alignment, and nothing else on it at all.

    Returns ``None`` when the template places no Степень field — then there is
    nowhere to overprint and no sheet worth handing over.
    """
    degree_fields = [field for field in fields if field.get("type") == _DEGREE_FIELD_TYPE]
    text = degree.strip()
    if not degree_fields or not text:
        return None

    pages = PdfReader(BytesIO(backing_pdf)).pages
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    for index, page in enumerate(pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        # Per page, before anything is drawn on it: the sheet has to line up with the
        # printed diploma it is fed over, so its geometry is the template's.
        c.setPageSize((width, height))
        for field in degree_fields:
            if int(field.get("page", 1)) == index:
                _draw_field(c, field, text, width, height)
        c.showPage()
    c.save()
    return buffer.getvalue()
