"""Reading an uploaded font file, and refusing the ones a diploma cannot be set in.

The gate on the upload path. It answers two questions, and both of them have to be answered
*here* — before the file is stored and offered in a dropdown — because the alternative is
finding out on a printed diploma at a ceremony.

**Can the renderer embed it?** reportlab embeds TrueType outlines. A ``.otf`` with CFF
outlines is a perfectly good font that it cannot use at all, and that is the single most
likely thing an organizer will try to upload, so the refusal says so in words they can act
on rather than "неподдерживаемый файл".

**Does it cover Cyrillic?** A Latin-only face draws a Russian surname as empty boxes. The
check is the 66 Russian letters against the file's own character map — cheap, exact, and it
catches the case where a beautiful display font simply was not made for this language.

The family and the variant are read from the file's ``name`` table rather than its filename.
An organizer uploads ``myfont-final(2).ttf`` and means Montserrat Bold; the file knows that
and the filename does not.
"""

from __future__ import annotations

import re
from typing import Final

from reportlab.pdfbase.ttfonts import TTFontFile

from apps.diplomas.application.font_library import FontInspection
from apps.diplomas.domain.fonts import CYRILLIC_SAMPLE, FontFileRejectedError, FontVariant

__all__ = ["ReportLabFontInspector"]

#: Anything past this is not a font somebody meant to upload. Generous: a CJK face with a
#: full Cyrillic range legitimately runs to several megabytes.
MAX_FONT_BYTES: Final = 12 * 1024 * 1024

#: How many of the 66 letters may be missing before the face is unusable. Zero: a surname
#: with one box in it is as wrong as a surname of boxes.
_ALLOWED_MISSING: Final = 0

_BOLD_PATTERN = re.compile(r"\b(bold|black|heavy|semibold|demibold|extrabold|ultrabold)\b", re.IGNORECASE)
_ITALIC_PATTERN = re.compile(r"\b(italic|oblique)\b", re.IGNORECASE)


def _text(value: object) -> str:
    """reportlab hands back name-table entries as bytes."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace").strip()
    return str(value or "").strip()


class ReportLabFontInspector:
    """Concrete ``FontFaceInspector`` over reportlab's own TrueType parser.

    Deliberately the same parser the renderer uses: a file that passes here is a file the
    renderer can embed, because it is the very same code path that will embed it. A separate
    validation library could accept something reportlab then chokes on at render time.
    """

    def inspect(self, data: bytes) -> FontInspection:
        """Identify the face, or raise :class:`FontFileRejectedError` with a usable reason."""
        if not data:
            raise FontFileRejectedError("Файл пустой.")
        if len(data) > MAX_FONT_BYTES:
            raise FontFileRejectedError(f"Файл больше {MAX_FONT_BYTES // (1024 * 1024)} МБ — это не похоже на шрифт.")

        try:
            # reportlab's parser takes a path or a file-like; bytes go in through a buffer so
            # nothing has to touch the disk before the file has been accepted.
            from io import BytesIO

            face = TTFontFile(BytesIO(data), validate=0)
        except Exception as exc:
            raise FontFileRejectedError(
                "Не удалось прочитать файл как TrueType. Загрузите .ttf — файлы .otf с "
                "контурами CFF в PDF встроить нельзя, у большинства шрифтов есть версия .ttf."
            ) from exc

        missing = [char for char in CYRILLIC_SAMPLE if ord(char) not in face.charToGlyph]
        if len(missing) > _ALLOWED_MISSING:
            raise FontFileRejectedError(
                f"В шрифте нет кириллицы (не хватает {len(missing)} из {len(CYRILLIC_SAMPLE)} букв) — русские имена в дипломе останутся пустыми."
            )

        family = _text(getattr(face, "familyName", "")) or _text(getattr(face, "name", ""))
        if not family:
            raise FontFileRejectedError("В файле не указано название семейства.")

        return FontInspection(family=family, variant=self._variant(face))

    @staticmethod
    def _variant(face: TTFontFile) -> FontVariant:
        """Which of the four faces this file is.

        Read from the style name, not from the OS/2 or head flags: those come back as 0 even
        for a file whose own name says "Bold", so trusting them would file every weight of a
        family as its regular.

        The italic angle is a second, independent signal — a face named only "Oblique" in a
        language we did not parse still slants, and the angle says so.
        """
        style = f"{_text(getattr(face, 'styleName', ''))} {_text(getattr(face, 'fullName', ''))}"
        bold = bool(_BOLD_PATTERN.search(style))
        italic = bool(_ITALIC_PATTERN.search(style)) or abs(float(getattr(face, "italicAngle", 0.0) or 0.0)) > 1.0
        return FontVariant.of(bold=bold, italic=italic)
