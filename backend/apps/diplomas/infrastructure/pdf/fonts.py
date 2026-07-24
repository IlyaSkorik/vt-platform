"""Font registry for PDF rendering.

reportlab needs a Unicode TrueType font to draw Cyrillic. We bundle DejaVu
(Sans/Serif, regular/bold) as a guaranteed, permissively-licensed fallback and
register any real family TTFs an operator drops into this directory.

**Real families**: to render exactly like the editor (Montserrat, PT Sans, …),
place their TTFs here named ``<Family>-Regular.ttf`` / ``-Bold.ttf`` /
``-Italic.ttf`` / ``-BoldItalic.ttf`` (family spaces stripped, e.g.
``PTSans-Regular.ttf``). They are then used automatically. Proprietary families
(Arial, Times New Roman, Georgia) cannot be bundled and always fall back to
DejaVu of the matching class.
"""

from __future__ import annotations

import threading
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

__all__ = ["resolve_font"]

_FONTS_DIR = Path(__file__).parent / "fonts"

# Bundled fallbacks: (registered name, filename).
_FALLBACKS: dict[str, str] = {
    "DejaVuSans": "DejaVuSans.ttf",
    "DejaVuSans-Bold": "DejaVuSans-Bold.ttf",
    "DejaVuSerif": "DejaVuSerif.ttf",
    "DejaVuSerif-Bold": "DejaVuSerif-Bold.ttf",
}

# Families the editor treats as serif — everything else maps to the sans fallback.
_SERIF_FAMILIES = {"times new roman", "georgia", "times", "serif"}

_lock = threading.Lock()
_registered = False
#: normalized family -> {(bold, italic): registered font name}
_overrides: dict[str, dict[tuple[bool, bool], str]] = {}


def _norm(family: str) -> str:
    return "".join(family.split()).lower()


def _register() -> None:
    global _registered
    if _registered:
        return
    with _lock:
        if _registered:
            return
        for name, filename in _FALLBACKS.items():
            path = _FONTS_DIR / filename
            if path.exists():
                pdfmetrics.registerFont(TTFont(name, str(path)))
        # Real family TTFs dropped into the directory: <Family>-<Variant>.ttf.
        variants = {
            "Regular": (False, False),
            "Bold": (True, False),
            "Italic": (False, True),
            "BoldItalic": (True, True),
        }
        for path in sorted(_FONTS_DIR.glob("*.ttf")):
            stem = path.stem
            if "-" not in stem:
                continue
            family, _, variant = stem.rpartition("-")
            key = variants.get(variant)
            if key is None or family.startswith("DejaVu"):
                continue
            registered_name = stem
            pdfmetrics.registerFont(TTFont(registered_name, str(path)))
            _overrides.setdefault(_norm(family), {})[key] = registered_name
        _registered = True


def resolve_font(family: str, *, bold: bool, italic: bool) -> str:
    """The registered reportlab font name for a family + weight/style.

    Prefers a real family TTF when present; otherwise a DejaVu fallback of the
    matching class (serif vs sans). Bold falls back to regular if no bold TTF;
    italic has no synthesized slant (DejaVu bold/regular is used).
    """
    _register()
    override = _overrides.get(_norm(family))
    if override:
        for key in ((bold, italic), (bold, False), (False, italic), (False, False)):
            if key in override:
                return override[key]
    base = "DejaVuSerif" if _norm(family) in {_norm(f) for f in _SERIF_FAMILIES} else "DejaVuSans"
    return f"{base}-Bold" if bold else base
