"""The font vocabulary a diploma is drawn with.

A diploma is the one artifact on this platform where **what the organizer sees must be
what gets printed**. Everywhere else a font substitution is cosmetic; here it lands on a
document with a child's name on it, handed over at a ceremony. So the editor and the
renderer draw from one list, and that list is what this module describes.

Three ideas carry it:

* :class:`FontVariant` — the four faces a family is used in. Deliberately only four:
  regular, bold, italic, bold-italic are what the editor's B/I buttons can ask for, and a
  weight axis nothing can select would be a list of files nobody could reach.
* :class:`FontFace` — one file: a family, a variant, and where it came from. Bundled faces
  ship with the platform; uploaded ones are the organizer's own.
* :data:`FAMILY_ALIASES` — the names a template may already hold that no free file can ever
  satisfy. Arial, Times New Roman and Georgia are proprietary; the alias table is where
  each becomes a substitute that exists, so an old template keeps rendering and the choice
  is written down instead of happening silently in a renderer.

Framework-free (no Django, no reportlab). Reading a font file is infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from apps.diplomas.domain.exceptions import DiplomaError

__all__ = [
    "CYRILLIC_SAMPLE",
    "FAMILY_ALIASES",
    "FontFace",
    "FontFamilyExistsError",
    "FontFileRejectedError",
    "FontNotFoundError",
    "FontSource",
    "FontVariant",
    "normalize_family",
]

_FAMILY_MAX: Final = 120


class FontVariant(StrEnum):
    """One of the four faces a family is drawn in.

    The names double as the filename suffix a bundled face is discovered by
    (``Montserrat-BoldItalic.ttf``), so the enum is the naming convention rather than a
    parallel description of it.
    """

    REGULAR = "Regular"
    BOLD = "Bold"
    ITALIC = "Italic"
    BOLD_ITALIC = "BoldItalic"

    @classmethod
    def of(cls, *, bold: bool, italic: bool) -> FontVariant:
        """The variant a bold/italic pair asks for."""
        if bold and italic:
            return cls.BOLD_ITALIC
        if bold:
            return cls.BOLD
        if italic:
            return cls.ITALIC
        return cls.REGULAR

    @property
    def bold(self) -> bool:
        return self in {FontVariant.BOLD, FontVariant.BOLD_ITALIC}

    @property
    def italic(self) -> bool:
        return self in {FontVariant.ITALIC, FontVariant.BOLD_ITALIC}

    @property
    def fallbacks(self) -> tuple[FontVariant, ...]:
        """Which faces to accept instead, best first, when this one is absent.

        A family uploaded as regular-only must still render a bold field — as regular, not
        as a different family, because the family is what the organizer chose and the weight
        is a detail of it. Synthesizing a slant or a smear is deliberately not done: a faked
        bold on a diploma looks like a printing fault.
        """
        match self:
            case FontVariant.BOLD_ITALIC:
                return (FontVariant.BOLD, FontVariant.ITALIC, FontVariant.REGULAR)
            case FontVariant.BOLD:
                return (FontVariant.REGULAR,)
            case FontVariant.ITALIC:
                return (FontVariant.REGULAR,)
            case _:
                return ()


class FontSource(StrEnum):
    """Where a face came from, which is also who may delete it."""

    #: Ships with the platform. Always present, never removable.
    BUNDLED = "BUNDLED"
    #: Uploaded by an organizer. Theirs to add and to remove.
    UPLOADED = "UPLOADED"


@dataclass(frozen=True, slots=True)
class FontFace:
    """One font file: a family, a variant, and where to read it from.

    ``reference`` is opaque on purpose — a path inside the package for a bundled face, a
    ``/media/…`` reference for an uploaded one — because nothing above infrastructure should
    care which. ``registered_name`` is the name the PDF renderer knows the face by, unique
    across the whole catalog so two families can never collide in the renderer's registry.
    """

    family: str
    variant: FontVariant
    source: FontSource
    reference: str
    registered_name: str


#: The 66 Russian letters a face must cover to be usable here.
#:
#: Not a nicety: this platform prints Russian names, and a font without Cyrillic renders
#: them as empty boxes. A diploma with a blank where a child's surname should be is worse
#: than one in a family the organizer did not pick, so a face that fails this is refused at
#: upload rather than discovered at the ceremony.
CYRILLIC_SAMPLE: Final = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"


#: Family name → the family actually used to draw it.
#:
#: Every key is either proprietary (Arial, Times New Roman, Georgia — no licence lets us
#: ship them) or a generic CSS keyword. The values are free faces with full Cyrillic:
#: Liberation Sans and Liberation Serif are *metric-compatible* with Arial and Times New
#: Roman, so a template laid out against either keeps its line breaks exactly. Georgia has
#: no metric-compatible free equivalent that covers Cyrillic — the closest, Gelasio, has no
#: Cyrillic at all — so it maps to PT Serif, which is a substitution in look as well as in
#: metrics and is labelled as one in the editor.
FAMILY_ALIASES: Final[dict[str, str]] = {
    "arial": "Liberation Sans",
    "helvetica": "Liberation Sans",
    "timesnewroman": "Liberation Serif",
    "times": "Liberation Serif",
    "georgia": "PT Serif",
    "sans-serif": "Roboto",
    "serif": "PT Serif",
}


def normalize_family(family: str) -> str:
    """The comparison key for a family name: spaces removed, case folded.

    "PT Sans", "PTSans" and "pt sans" are one family under three spellings — a template
    stores what the editor put in it, a filename cannot hold a space, and an uploaded file
    names itself however its designer chose.
    """
    return "".join(str(family).split()).lower()


class FontFileRejectedError(DiplomaError):
    """Raised when an uploaded file cannot be used to draw a diploma.

    Covers both halves of "usable": the renderer must be able to embed it (TrueType
    outlines — a CFF-based ``.otf`` cannot be embedded by reportlab at all), and it must
    cover Cyrillic. The message says which, because "не подходит" is not something an
    organizer can act on.
    """

    code = "font_file_rejected"


class FontFamilyExistsError(DiplomaError):
    """Raised when an upload would replace a face the library already holds.

    Same family, same variant. Refused rather than overwritten: a template already points
    at that family by name, and silently swapping the file under it would change documents
    nobody asked to change.
    """

    code = "font_family_exists"


class FontNotFoundError(DiplomaError):
    """Raised when a referenced uploaded font does not exist (or is bundled)."""

    code = "font_not_found"
