"""The font catalog an organizer picks from, and the uploads that extend it.

One service over two sources. **Bundled** faces ship with the platform and are always
there; **uploaded** ones are the organizer's own files, and they are the whole point of this
module: without them a festival's diplomas can only ever be set in the seven families we
happened to choose, which for a document carrying a school's identity is not good enough.

The catalog is served to the editor rather than hard-coded in it, and that is what makes the
promise hold: the dropdown lists exactly the faces the renderer can draw, so a family can
never be selectable and unprintable at the same time. Adding a family is uploading a file —
no release, no deploy.

Two rules the service enforces, both of them about not lying to the organizer:

* **an upload must be drawable and must cover Cyrillic.** A CFF-based ``.otf`` cannot be
  embedded by the renderer at all, and a Latin-only face turns a Russian surname into empty
  boxes. Both are refused at upload, where the organizer can still do something about it,
  rather than discovered on the printed page.
* **an upload never replaces an existing face.** A template points at a family by name, so
  swapping the file underneath it would silently change documents that were already
  approved.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from apps.diplomas.domain.fonts import (
    FontFace,
    FontFamilyExistsError,
    FontNotFoundError,
    FontSource,
    FontVariant,
    normalize_family,
)

__all__ = [
    "FontCatalogFamilyView",
    "FontCatalogView",
    "FontFaceInspector",
    "FontFaceRepository",
    "FontFileStore",
    "FontInspection",
    "FontLibraryService",
    "FontVariantView",
    "UploadedFontView",
]


@dataclass(frozen=True, slots=True)
class FontInspection:
    """What reading a font file told us about it.

    ``family`` and ``variant`` come from the file's own name table, not from its filename:
    an organizer uploads "myfont-final(2).ttf" and means Montserrat Bold, and the file knows
    that even when its name does not.
    """

    family: str
    variant: FontVariant


@dataclass(frozen=True, slots=True)
class FontVariantView:
    """One face of a family, as the editor needs it to build an ``@font-face`` rule."""

    variant: FontVariant
    bold: bool
    italic: bool
    #: Where the browser fetches the file from. Public by necessity — a browser requests
    #: ``@font-face`` sources without the Authorization header, so a font behind a token
    #: would simply never load in the editor.
    file_url: str


@dataclass(frozen=True, slots=True)
class FontCatalogFamilyView:
    """One family the editor may offer, with every face it can actually draw."""

    family: str
    source: FontSource
    variants: tuple[FontVariantView, ...]
    #: Set when this family is drawn with a different one — the proprietary names an old
    #: template may still hold. The editor shows it so the substitution is visible.
    substituted_by: str | None = None
    #: Uploaded families carry the id they are deleted by; bundled ones cannot be deleted.
    id: str | None = None


@dataclass(frozen=True, slots=True)
class FontCatalogView:
    """Everything the editor's font dropdown is built from."""

    families: tuple[FontCatalogFamilyView, ...]


@dataclass(frozen=True, slots=True)
class UploadedFontView:
    """One uploaded face, as the library screen lists it."""

    id: str
    family: str
    variant: FontVariant
    original_filename: str
    file_url: str
    size_bytes: int
    uploaded_at: datetime


class FontFaceInspector(Protocol):
    """Reads a font file and decides whether a diploma can be drawn with it."""

    def inspect(self, data: bytes) -> FontInspection:
        """Identify the family and variant, or raise ``FontFileRejectedError``.

        Rejects anything the renderer cannot embed and anything that does not cover
        Cyrillic — see the module docstring for why those are the same kind of failure.
        """
        ...


class FontFaceRepository(Protocol):
    """Persistence port for uploaded faces."""

    def new_id(self) -> uuid.UUID:
        """Mint a fresh, time-ordered id."""
        ...

    def exists(self, *, family: str, variant: FontVariant) -> bool:
        """Whether the library already holds this family in this variant."""
        ...

    def add(
        self,
        *,
        font_id: uuid.UUID,
        family: str,
        variant: FontVariant,
        reference: str,
        original_filename: str,
        size_bytes: int,
        now: datetime,
    ) -> None:
        """Record an uploaded face."""
        ...

    def list_uploaded(self) -> Sequence[UploadedFontView]:
        """Every uploaded face, newest first."""
        ...

    def faces(self) -> Sequence[FontFace]:
        """Every uploaded face in the renderer's vocabulary."""
        ...

    def remove(self, font_id: uuid.UUID) -> str | None:
        """Soft-delete one face; return its storage reference, or ``None`` if unknown."""
        ...


class FontFileStore(Protocol):
    """Where an uploaded font file is kept."""

    def store(self, *, family: str, variant: FontVariant, data: bytes) -> str:
        """Persist the file; return the ``/media/…`` reference it is read back by."""
        ...

    def url_for(self, reference: str) -> str:
        """The public URL a browser fetches this reference from."""
        ...


class BundledFontProvider(Protocol):
    """The faces that ship with the platform."""

    def faces(self) -> Sequence[FontFace]:
        """Every bundled face."""
        ...

    def url_for(self, face: FontFace) -> str:
        """The public URL a browser fetches this bundled face from."""
        ...


class FontLibraryService:
    """The catalog, and the uploads that extend it."""

    def __init__(
        self,
        *,
        repository: FontFaceRepository,
        store: FontFileStore,
        inspector: FontFaceInspector,
        bundled: BundledFontProvider,
        aliases: dict[str, str],
    ) -> None:
        self._repository = repository
        self._store = store
        self._inspector = inspector
        self._bundled = bundled
        self._aliases = aliases

    def register(self, *, data: bytes, original_filename: str, now: datetime) -> UploadedFontView:
        """Add one font file to the library.

        The family and variant are read from the file, so an organizer uploads four files for
        a family and gets a family — they never have to name anything, and they cannot name
        it wrongly.
        """
        inspection = self._inspector.inspect(data)
        if self._repository.exists(family=inspection.family, variant=inspection.variant):
            raise FontFamilyExistsError(
                f"«{inspection.family} {inspection.variant.value}» уже есть в библиотеке. Удалите старый файл, если хотите заменить его."
            )
        font_id = self._repository.new_id()
        reference = self._store.store(family=inspection.family, variant=inspection.variant, data=data)
        self._repository.add(
            font_id=font_id,
            family=inspection.family,
            variant=inspection.variant,
            reference=reference,
            original_filename=original_filename,
            size_bytes=len(data),
            now=now,
        )
        return UploadedFontView(
            id=str(font_id),
            family=inspection.family,
            variant=inspection.variant,
            original_filename=original_filename,
            file_url=self._store.url_for(reference),
            size_bytes=len(data),
            uploaded_at=now,
        )

    def remove(self, font_id: str) -> None:
        """Drop one uploaded face from the library.

        The file itself is left in storage: a diploma rendered last week is a document that
        already exists, and nothing about deleting a font from a dropdown should reach back
        into it.
        """
        try:
            parsed = uuid.UUID(str(font_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise FontNotFoundError(f"{font_id!r} is not a font id.") from exc
        if self._repository.remove(parsed) is None:
            raise FontNotFoundError(f"Font {font_id} is not in the library.")

    def list_uploaded(self) -> tuple[UploadedFontView, ...]:
        """The uploaded faces, for the library screen."""
        return tuple(self._repository.list_uploaded())

    def catalog(self) -> FontCatalogView:
        """Every family the editor may offer, uploaded ones first.

        Uploaded before bundled because an organizer who took the trouble to upload their
        festival's typeface should not have to scroll past ours to find it.

        An uploaded family that shadows a bundled name wins outright: that is the escape
        hatch for "your Montserrat is not the Montserrat we use", and it is the only way a
        platform-shipped family can be overridden.
        """
        uploaded = self._group(self._bundled_urls(self._repository.faces(), uploaded=True))
        bundled = self._group(self._bundled_urls(self._bundled.faces(), uploaded=False))

        families: list[FontCatalogFamilyView] = []
        seen = set()
        for family in uploaded:
            families.append(family)
            seen.add(normalize_family(family.family))
        for family in bundled:
            if normalize_family(family.family) not in seen:
                families.append(family)
                seen.add(normalize_family(family.family))

        # The proprietary names, offered as what they really are. Listed after the real
        # families so nobody picks "Arial" without having seen the substitute first.
        by_key = {normalize_family(item.family): item for item in families}
        for alias, target in self._aliases.items():
            if alias in by_key or alias in {"serif", "sans-serif"}:
                continue
            resolved = by_key.get(normalize_family(target))
            if resolved is None:
                continue
            families.append(
                FontCatalogFamilyView(
                    family=_ALIAS_LABELS.get(alias, alias),
                    source=resolved.source,
                    variants=resolved.variants,
                    substituted_by=resolved.family,
                )
            )
        return FontCatalogView(families=tuple(families))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _bundled_urls(self, faces: Sequence[FontFace], *, uploaded: bool) -> list[tuple[FontFace, str]]:
        """Pair each face with the URL a browser fetches it from."""
        return [(face, self._store.url_for(face.reference) if uploaded else self._bundled.url_for(face)) for face in faces]

    @staticmethod
    def _group(faces: Sequence[tuple[FontFace, str]]) -> list[FontCatalogFamilyView]:
        """Collapse faces into families, each carrying its variants in canonical order."""
        by_family: dict[str, list[tuple[FontFace, str]]] = {}
        for face, url in faces:
            by_family.setdefault(face.family, []).append((face, url))
        grouped: list[FontCatalogFamilyView] = []
        for family, entries in sorted(by_family.items(), key=lambda item: item[0].lower()):
            order = list(FontVariant)
            entries.sort(key=lambda item: order.index(item[0].variant))
            grouped.append(
                FontCatalogFamilyView(
                    family=family,
                    source=entries[0][0].source,
                    variants=tuple(
                        FontVariantView(
                            variant=face.variant,
                            bold=face.variant.bold,
                            italic=face.variant.italic,
                            file_url=url,
                        )
                        for face, url in entries
                    ),
                )
            )
        return grouped


#: How an alias is spelled in the dropdown. The keys are normalized for lookup, and a
#: reader of a font list should still see "Times New Roman" rather than "timesnewroman".
_ALIAS_LABELS: dict[str, str] = {
    "arial": "Arial",
    "helvetica": "Helvetica",
    "timesnewroman": "Times New Roman",
    "times": "Times",
    "georgia": "Georgia",
}
