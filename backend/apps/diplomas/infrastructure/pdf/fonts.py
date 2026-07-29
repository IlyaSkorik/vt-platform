"""Font registry for PDF rendering.

The renderer's half of the promise that a diploma prints in the family the organizer
picked. Two sources feed it, in this order:

1. **uploaded faces** — the organizer's own files, read from the font library. They win
   outright, including over a bundled family of the same name: "your Montserrat is not the
   Montserrat we use" is a real objection and this is its answer.
2. **bundled faces** — the families that ship with the platform, discovered from this
   directory by the ``<Family>-<Variant>.ttf`` convention. Every one of them covers
   Cyrillic; that is a hard requirement, because a face without it renders a Russian
   surname as empty boxes.

Anything still unresolved goes through :data:`FAMILY_ALIASES` — the proprietary names an
old template may hold — and only then to DejaVu, which is the last resort rather than the
usual outcome it used to be.

**Static faces only.** A variable font (``Montserrat[wght].ttf``) loads here without
complaint and then draws its default instance, so a bold field would come out regular with
nothing anywhere reporting a problem. The bundled files are static instances for exactly
that reason, and an upload is inspected rather than trusted.

The uploaded index is cached per process with a short TTL. Renders happen in Celery workers
as well as in web processes, so a worker that cached its index before an upload has to pick
the new face up on its own — invalidating the caller's cache cannot reach it.

An uploaded face's reference is a **storage** reference, not a path: in production the files
live in S3. It is turned into a local file by the injected ``materialize`` callable, and only
for the one face a render actually draws — resolving the whole index would download a font
library to embed one font.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.diplomas.domain.fonts import (
    FAMILY_ALIASES,
    FontFace,
    FontSource,
    FontVariant,
    normalize_family,
)

__all__ = [
    "BUNDLED_FONTS_DIR",
    "DjangoBundledFontProvider",
    "bundled_faces",
    "bundled_font_path",
    "invalidate_uploaded_fonts",
    "resolve_font",
    "set_uploaded_face_source",
]

logger = logging.getLogger(__name__)

BUNDLED_FONTS_DIR = Path(__file__).parent / "fonts"

#: The guaranteed fallbacks. Registered under their own names and used only when a family
#: cannot be resolved any other way.
_FALLBACKS: dict[str, str] = {
    "DejaVuSans": "DejaVuSans.ttf",
    "DejaVuSans-Bold": "DejaVuSans-Bold.ttf",
    "DejaVuSerif": "DejaVuSerif.ttf",
    "DejaVuSerif-Bold": "DejaVuSerif-Bold.ttf",
}

#: Which fallback class an unresolvable family lands in.
_SERIF_HINTS = {"times", "timesnewroman", "georgia", "serif", "ptserif", "liberationserif"}

#: How long a process trusts its view of the uploaded library. Short, because the cost of
#: being stale is an organizer uploading a font and not seeing it, and the cost of being
#: fresh is one indexed query a minute per process.
_UPLOADED_TTL_SECONDS = 30.0

_lock = threading.Lock()
_bundled_registered = False
#: normalized family -> {variant: FontFace}
_bundled_index: dict[str, dict[FontVariant, FontFace]] = {}
_registered_names: set[str] = set()

_uploaded_source: Callable[[], Sequence[FontFace]] | None = None
#: Turns an uploaded face's storage reference into a local path reportlab can open, or
#: ``None`` when storage cannot produce one.
_materialize: Callable[[FontFace], str | None] | None = None
_uploaded_index: dict[str, dict[FontVariant, FontFace]] = {}
_uploaded_loaded_at = 0.0


def set_uploaded_face_source(
    source: Callable[[], Sequence[FontFace]] | None,
    *,
    materialize: Callable[[FontFace], str | None] | None = None,
) -> None:
    """Tell the registry where to read uploaded faces from, and how to get their bytes.

    Both injected by the composition root rather than imported here: this module is loaded by
    the renderer, and a direct import of the repository would put a database dependency inside
    the one component that has to work in a worker with nothing else wired up.

    ``materialize`` exists because an uploaded face's reference points at object storage in
    production. Without it an S3 deployment would list an organizer's fonts in the editor and
    quietly draw every diploma in a bundled family instead.
    """
    global _uploaded_source, _materialize, _uploaded_loaded_at
    with _lock:
        _uploaded_source = source
        _materialize = materialize
        _uploaded_loaded_at = 0.0


def invalidate_uploaded_fonts() -> None:
    """Forget this process's view of the uploaded library (after an upload or a delete)."""
    global _uploaded_loaded_at
    with _lock:
        _uploaded_loaded_at = 0.0


def _scan_bundled() -> None:
    """Index the bundled directory once: ``<Family>-<Variant>.ttf``."""
    global _bundled_registered
    if _bundled_registered:
        return
    with _lock:
        if _bundled_registered:
            return
        variants = {variant.value: variant for variant in FontVariant}
        for path in sorted(BUNDLED_FONTS_DIR.glob("*.ttf")):
            stem = path.stem
            if stem in _FALLBACKS:
                continue
            family_part, _, variant_part = stem.rpartition("-")
            variant = variants.get(variant_part)
            if not family_part or variant is None:
                # Not a face we can place — a bundled file must say which variant it is, and
                # guessing would put a regular weight where a bold was asked for.
                continue
            face = FontFace(
                family=_display_family(family_part),
                variant=variant,
                source=FontSource.BUNDLED,
                reference=str(path),
                registered_name=f"vtb-{stem}",
            )
            _bundled_index.setdefault(normalize_family(face.family), {})[variant] = face
        _bundled_registered = True


def _display_family(stem_family: str) -> str:
    """Turn a filename's family part into the name a human reads.

    ``LiberationSans`` → "Liberation Sans", ``PTSerif`` → "PT Serif". The editor shows this
    string and a template stores it, so it has to be the spelling a person would type.
    """
    known = {
        "liberationsans": "Liberation Sans",
        "liberationserif": "Liberation Serif",
        "ptsans": "PT Sans",
        "ptserif": "PT Serif",
        "opensans": "Open Sans",
        "montserrat": "Montserrat",
        "roboto": "Roboto",
    }
    return known.get(stem_family.lower(), stem_family)


def _uploaded() -> dict[str, dict[FontVariant, FontFace]]:
    """This process's view of the uploaded library, refreshed when it goes stale."""
    global _uploaded_index, _uploaded_loaded_at
    if _uploaded_source is None:
        return {}
    if time.monotonic() - _uploaded_loaded_at < _UPLOADED_TTL_SECONDS:
        return _uploaded_index
    with _lock:
        source = _uploaded_source
        if source is None:
            return {}
        index: dict[str, dict[FontVariant, FontFace]] = {}
        try:
            for face in source():
                index.setdefault(normalize_family(face.family), {})[face.variant] = face
        except Exception:
            # Falling back to the bundled families is a worse diploma; failing the render is
            # no diploma at all. The bundled set always covers Cyrillic, so the document is
            # still correct, just not in the chosen family.
            return _uploaded_index
        _uploaded_index = index
        _uploaded_loaded_at = time.monotonic()
        return _uploaded_index


def _register(face: FontFace) -> str | None:
    """Register a face with reportlab once; return the name it is known by, or ``None``.

    ``None`` means this face cannot be drawn right now — its file could not be fetched from
    storage, or reportlab refused it. The caller then carries on down its fallback chain, so a
    single unreachable upload costs the chosen family rather than the whole diploma.
    """
    if face.registered_name in _registered_names:
        return face.registered_name

    path = face.reference
    if face.source is FontSource.UPLOADED:
        if _materialize is None:
            # Nothing wired up to fetch it: on a filesystem backend the reference happens to be
            # openable, so trying is still better than refusing outright.
            path = face.reference
        else:
            local = _materialize(face)
            if local is None:
                return None
            path = local

    with _lock:
        if face.registered_name not in _registered_names:
            try:
                pdfmetrics.registerFont(TTFont(face.registered_name, path))
            except Exception:
                logger.warning("Could not register font %s from %s.", face.registered_name, path, exc_info=True)
                return None
            _registered_names.add(face.registered_name)
    return face.registered_name


def _register_fallbacks() -> None:
    for name, filename in _FALLBACKS.items():
        if name in _registered_names:
            continue
        path = BUNDLED_FONTS_DIR / filename
        if path.exists():
            with _lock:
                if name not in _registered_names:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                    _registered_names.add(name)


def _candidates(key: str, variant: FontVariant) -> Iterator[FontFace]:
    """Every face that could draw this family and variant, best first.

    Yields rather than returns one, because a face can be *found* and still not be
    *drawable*: an uploaded font whose object storage is unreachable is the case this exists
    for. The caller tries them in turn, so an unreachable upload falls through to the bundled
    family of the same name — which is sitting right there — instead of skipping to DejaVu.

    Order within a family is the requested variant, then its own fallbacks: a family's regular
    weight is a better answer for a missing bold than a different family's bold.
    """
    for index in (_uploaded(), _bundled_index):
        faces = index.get(key)
        if not faces:
            continue
        for candidate in (variant, *variant.fallbacks):
            face = faces.get(candidate)
            if face is not None:
                yield face


def resolve_font(family: str, *, bold: bool, italic: bool) -> str:
    """The registered reportlab font name for a family and a weight/style.

    Resolution order: the family itself (uploaded, then bundled), then whatever
    :data:`FAMILY_ALIASES` maps it to, then DejaVu of the matching class. A missing bold
    falls back to that family's regular rather than to another family — the family is what
    was chosen and the weight is a detail of it.
    """
    _scan_bundled()
    variant = FontVariant.of(bold=bold, italic=italic)
    key = normalize_family(family)

    for candidate_key in (key, normalize_family(FAMILY_ALIASES.get(key, ""))):
        if not candidate_key:
            continue
        for face in _candidates(candidate_key, variant):
            registered = _register(face)
            if registered is not None:
                return registered
            # Found but not drawable — an upload whose storage is unreachable. Carry on to the
            # bundled face of the same family, then the alias, then DejaVu. A diploma in the
            # wrong typeface is bad; a render that fails is worse.

    _register_fallbacks()
    base = "DejaVuSerif" if key in _SERIF_HINTS else "DejaVuSans"
    return f"{base}-Bold" if bold else base


def bundled_faces() -> tuple[FontFace, ...]:
    """Every bundled face, for the catalog the editor is built from."""
    _scan_bundled()
    return tuple(face for faces in _bundled_index.values() for face in faces.values())


def bundled_font_path(family: str, variant: str) -> Path | None:
    """The file behind one bundled face, or ``None``.

    The public font endpoint resolves through this rather than joining a path from the URL:
    the answer can only ever be a file this directory already indexed, which is what makes
    ``../../etc/passwd`` a miss instead of a traversal.
    """
    _scan_bundled()
    faces = _bundled_index.get(normalize_family(family))
    if not faces:
        return None
    try:
        wanted = FontVariant(variant)
    except ValueError:
        return None
    face = faces.get(wanted)
    return None if face is None else Path(face.reference)


class DjangoBundledFontProvider:
    """Concrete ``BundledFontProvider``: the platform's own faces and their public URLs."""

    def faces(self) -> tuple[FontFace, ...]:
        return bundled_faces()

    def url_for(self, face: FontFace) -> str:
        """Where a browser fetches this bundled face from.

        A relative path, resolved by the client against the API origin — the same shape every
        other media reference in this context uses.
        """
        return f"/api/v1/public/diploma-fonts/{normalize_family(face.family)}/{face.variant.value}.ttf"
