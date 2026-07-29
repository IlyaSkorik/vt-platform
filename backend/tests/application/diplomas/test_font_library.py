"""Use-case tests for the font library (in-memory ports, no database, no font files).

The catalog is what the editor's dropdown is built from, so these tests are about one
promise: **everything offered is drawable, and everything drawable is offered**. The rest —
uploads winning over bundled families, proprietary names resolving to a substitute that
exists, a second upload of the same face being refused — are the cases where that promise is
easy to break.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from apps.diplomas.application.font_library import (
    FontInspection,
    FontLibraryService,
    UploadedFontView,
)
from apps.diplomas.domain.fonts import (
    FAMILY_ALIASES,
    FontFace,
    FontFamilyExistsError,
    FontFileRejectedError,
    FontNotFoundError,
    FontSource,
    FontVariant,
    normalize_family,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def bundled(family: str, variant: FontVariant = FontVariant.REGULAR) -> FontFace:
    return FontFace(
        family=family,
        variant=variant,
        source=FontSource.BUNDLED,
        reference=f"/pkg/{normalize_family(family)}-{variant.value}.ttf",
        registered_name=f"vtb-{normalize_family(family)}-{variant.value}",
    )


class StubBundled:
    def __init__(self, *faces: FontFace) -> None:
        self._faces = list(faces)

    def faces(self) -> Sequence[FontFace]:
        return tuple(self._faces)

    def url_for(self, face: FontFace) -> str:
        return f"/api/v1/public/diploma-fonts/{normalize_family(face.family)}/{face.variant.value}.ttf"


class StubInspector:
    """Reports whatever the test says the file is — or refuses it."""

    def __init__(self, *, result: FontInspection | None = None, reason: str | None = None) -> None:
        self._result = result
        self._reason = reason
        self.calls = 0

    def inspect(self, data: bytes) -> FontInspection:
        self.calls += 1
        if self._reason is not None:
            raise FontFileRejectedError(self._reason)
        assert self._result is not None
        return self._result


class InMemoryRepository:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, dict[str, object]] = {}

    def new_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def exists(self, *, family: str, variant: FontVariant) -> bool:
        return any(row["family_key"] == normalize_family(family) and row["variant"] is variant for row in self.rows.values())

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
        self.rows[font_id] = {
            "family": family,
            "family_key": normalize_family(family),
            "variant": variant,
            "reference": reference,
            "original_filename": original_filename,
            "size_bytes": size_bytes,
            "now": now,
        }

    def list_uploaded(self) -> Sequence[UploadedFontView]:
        return [
            UploadedFontView(
                id=str(font_id),
                family=str(row["family"]),
                variant=row["variant"],  # type: ignore[arg-type]
                original_filename=str(row["original_filename"]),
                file_url=str(row["reference"]),
                size_bytes=int(row["size_bytes"]),  # type: ignore[call-overload]
                uploaded_at=row["now"],  # type: ignore[arg-type]
            )
            for font_id, row in self.rows.items()
        ]

    def faces(self) -> Sequence[FontFace]:
        return [
            FontFace(
                family=str(row["family"]),
                variant=row["variant"],  # type: ignore[arg-type]
                source=FontSource.UPLOADED,
                reference=str(row["reference"]),
                registered_name=f"vtu-{font_id.hex}",
            )
            for font_id, row in self.rows.items()
        ]

    def remove(self, font_id: uuid.UUID) -> str | None:
        row = self.rows.pop(font_id, None)
        return None if row is None else str(row["reference"])


class RecordingStore:
    def __init__(self) -> None:
        self.stored: list[tuple[str, FontVariant, int]] = []

    def store(self, *, family: str, variant: FontVariant, data: bytes) -> str:
        self.stored.append((family, variant, len(data)))
        return f"/media/diplomas/fonts/{normalize_family(family)}-{variant.value}.ttf"

    def url_for(self, reference: str) -> str:
        return reference


def build(
    *bundled_faces: FontFace,
    inspector: StubInspector | None = None,
) -> tuple[FontLibraryService, InMemoryRepository, RecordingStore, StubInspector]:
    repository = InMemoryRepository()
    store = RecordingStore()
    insp = inspector or StubInspector(result=FontInspection(family="Inter", variant=FontVariant.REGULAR))
    service = FontLibraryService(
        repository=repository,
        store=store,
        inspector=insp,
        bundled=StubBundled(*bundled_faces),
        aliases=FAMILY_ALIASES,
    )
    return service, repository, store, insp


def families_of(service: FontLibraryService) -> list[str]:
    return [family.family for family in service.catalog().families]


class TestUpload:
    def test_the_family_and_variant_come_from_the_file_not_its_name(self) -> None:
        # The organizer uploads "myfont-final(2).ttf" and means Montserrat Bold. The file
        # knows that; the filename does not.
        service, repository, store, _ = build(inspector=StubInspector(result=FontInspection(family="Montserrat", variant=FontVariant.BOLD)))
        view = service.register(data=b"x" * 100, original_filename="myfont-final(2).ttf", now=NOW)
        assert view.family == "Montserrat"
        assert view.variant is FontVariant.BOLD
        assert view.original_filename == "myfont-final(2).ttf"
        assert store.stored == [("Montserrat", FontVariant.BOLD, 100)]
        assert len(repository.rows) == 1

    def test_a_rejected_file_is_never_stored(self) -> None:
        service, repository, store, _ = build(inspector=StubInspector(reason="нет кириллицы"))
        with pytest.raises(FontFileRejectedError):
            service.register(data=b"x", original_filename="latin.ttf", now=NOW)
        assert store.stored == []
        assert repository.rows == {}

    def test_the_same_face_twice_is_refused_rather_than_overwritten(self) -> None:
        # A template points at the family by name; swapping the file underneath it would
        # change documents nobody asked to change.
        service, _repo, store, _ = build(inspector=StubInspector(result=FontInspection(family="Inter", variant=FontVariant.REGULAR)))
        service.register(data=b"x", original_filename="Inter.ttf", now=NOW)
        with pytest.raises(FontFamilyExistsError):
            service.register(data=b"y", original_filename="Inter-again.ttf", now=NOW)
        assert len(store.stored) == 1

    def test_another_variant_of_the_same_family_is_fine(self) -> None:
        service, repository, _store, _ = build(inspector=StubInspector(result=FontInspection(family="Inter", variant=FontVariant.REGULAR)))
        service.register(data=b"x", original_filename="Inter-Regular.ttf", now=NOW)
        service._inspector = StubInspector(result=FontInspection(family="Inter", variant=FontVariant.BOLD))
        service.register(data=b"y", original_filename="Inter-Bold.ttf", now=NOW)
        assert len(repository.rows) == 2
        inter = next(family for family in service.catalog().families if family.family == "Inter")
        assert len(inter.variants) == 2


class TestRemove:
    def test_an_unknown_font_is_refused(self) -> None:
        service, _repo, _store, _ = build()
        with pytest.raises(FontNotFoundError):
            service.remove(str(uuid.uuid4()))

    def test_a_malformed_id_is_the_same_refusal_not_a_crash(self) -> None:
        service, _repo, _store, _ = build()
        with pytest.raises(FontNotFoundError):
            service.remove("not-a-uuid")

    def test_removing_takes_the_family_out_of_the_catalog(self) -> None:
        service, _repo, _store, _ = build()
        view = service.register(data=b"x", original_filename="Inter.ttf", now=NOW)
        assert "Inter" in families_of(service)
        service.remove(view.id)
        assert "Inter" not in families_of(service)


class TestCatalog:
    def test_it_lists_the_bundled_families(self) -> None:
        service, _repo, _store, _ = build(bundled("Montserrat"), bundled("PT Serif"))
        assert "Montserrat" in families_of(service)
        assert "PT Serif" in families_of(service)

    def test_variants_come_back_in_canonical_order(self) -> None:
        service, _repo, _store, _ = build(
            bundled("Montserrat", FontVariant.BOLD_ITALIC),
            bundled("Montserrat", FontVariant.REGULAR),
            bundled("Montserrat", FontVariant.BOLD),
        )
        family = next(f for f in service.catalog().families if f.family == "Montserrat")
        assert [v.variant for v in family.variants] == [
            FontVariant.REGULAR,
            FontVariant.BOLD,
            FontVariant.BOLD_ITALIC,
        ]

    def test_every_variant_carries_a_url_the_browser_can_fetch(self) -> None:
        # Without this the editor previews in a fallback face while the PDF uses the real
        # one — the exact mismatch the whole feature exists to remove.
        service, _repo, _store, _ = build(bundled("Montserrat"))
        family = next(f for f in service.catalog().families if f.family == "Montserrat")
        assert all(variant.file_url for variant in family.variants)

    def test_uploaded_families_come_before_bundled_ones(self) -> None:
        service, _repo, _store, _ = build(bundled("Montserrat"))
        service.register(data=b"x", original_filename="Inter.ttf", now=NOW)
        assert families_of(service)[0] == "Inter"

    def test_an_upload_overrides_a_bundled_family_of_the_same_name(self) -> None:
        # "Your Montserrat is not the Montserrat we use" is a real objection, and this is the
        # only way a platform-shipped family can be replaced.
        service, _repo, _store, _ = build(
            bundled("Montserrat"),
            inspector=StubInspector(result=FontInspection(family="Montserrat", variant=FontVariant.REGULAR)),
        )
        service.register(data=b"x", original_filename="OurMontserrat.ttf", now=NOW)
        montserrat = [f for f in service.catalog().families if f.family == "Montserrat"]
        assert len(montserrat) == 1
        assert montserrat[0].source is FontSource.UPLOADED

    def test_proprietary_names_are_offered_as_the_substitute_they_really_are(self) -> None:
        service, _repo, _store, _ = build(bundled("Liberation Sans"), bundled("Liberation Serif"), bundled("PT Serif"))
        by_name = {family.family: family for family in service.catalog().families}
        assert by_name["Arial"].substituted_by == "Liberation Sans"
        assert by_name["Times New Roman"].substituted_by == "Liberation Serif"
        assert by_name["Georgia"].substituted_by == "PT Serif"

    def test_a_real_family_is_never_marked_as_a_substitute(self) -> None:
        service, _repo, _store, _ = build(bundled("Liberation Sans"))
        real = next(f for f in service.catalog().families if f.family == "Liberation Sans")
        assert real.substituted_by is None

    def test_an_alias_whose_substitute_is_absent_is_not_offered(self) -> None:
        # Offering "Arial" with nothing behind it would put a family in the dropdown that the
        # renderer cannot draw, which is the one thing the catalog exists to prevent.
        service, _repo, _store, _ = build(bundled("Montserrat"))
        assert "Arial" not in families_of(service)

    def test_the_css_keywords_are_not_offered_as_families(self) -> None:
        # `serif` and `sans-serif` resolve for an old template's sake; they are not names a
        # person picks from a list.
        service, _repo, _store, _ = build(bundled("PT Serif"), bundled("Roboto"))
        assert "serif" not in families_of(service)
        assert "sans-serif" not in families_of(service)

    def test_an_empty_library_is_an_empty_catalog_not_an_error(self) -> None:
        service, _repo, _store, _ = build()
        assert service.catalog().families == ()
