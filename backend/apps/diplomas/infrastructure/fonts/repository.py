"""Django adapters for the font library: the face repository and the file store.

Nothing here decides anything — the service already asked the inspector whether a file is
usable and whether the library holds it. These two adapters put the bytes somewhere and the
row in a table.

The one judgement they do make is about deletion: a removed face is soft-deleted and its file
is **left in storage**. A diploma rendered last week is a document that already exists, and
nothing about tidying a dropdown should be able to reach back into it.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from collections.abc import Sequence
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.diplomas.application.font_library import UploadedFontView
from apps.diplomas.domain.fonts import FontFace, FontSource, FontVariant, normalize_family
from apps.diplomas.infrastructure.models import FontFaceModel, uuid7

__all__ = ["DjangoFontFaceRepository", "DjangoFontFileStore"]

_MEDIA_PREFIX = "/media/"


def _unguessable(*parts: str) -> str:
    """A short, stable, non-enumerable path segment (same scheme as the diploma trees)."""
    digest = hmac.new(settings.SECRET_KEY.encode(), "/".join(parts).encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


def _storage_key(reference: str) -> str:
    return reference[len(_MEDIA_PREFIX) :] if reference.startswith(_MEDIA_PREFIX) else reference


class DjangoFontFaceRepository:
    """Concrete ``FontFaceRepository`` over PostgreSQL."""

    def new_id(self) -> uuid.UUID:
        return uuid7()

    def exists(self, *, family: str, variant: FontVariant) -> bool:
        return FontFaceModel.objects.filter(
            family_key=normalize_family(family),
            variant=variant.value,
            deleted_at__isnull=True,
        ).exists()

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
        FontFaceModel.objects.create(
            id=font_id,
            family=family,
            family_key=normalize_family(family),
            variant=variant.value,
            file_reference=reference,
            original_filename=original_filename[:255],
            size_bytes=size_bytes,
            created_at=now,
            updated_at=now,
        )

    def list_uploaded(self) -> Sequence[UploadedFontView]:
        rows = FontFaceModel.objects.filter(deleted_at__isnull=True).order_by("family", "variant")
        return [
            UploadedFontView(
                id=str(row.id),
                family=row.family,
                variant=FontVariant(row.variant),
                original_filename=row.original_filename,
                file_url=row.file_reference,
                size_bytes=int(row.size_bytes),
                uploaded_at=row.created_at,
            )
            for row in rows
        ]

    def faces(self) -> Sequence[FontFace]:
        """Every uploaded face in the renderer's vocabulary.

        ``reference`` stays the **storage** reference rather than a local path: on S3 there is
        no local path yet, and producing one here would mean downloading every uploaded font
        each time this index is rebuilt — for a render that needs one of them. The registry
        materializes the face it actually draws, through
        :class:`~apps.diplomas.infrastructure.fonts.cache.FontFileCache`.
        """
        rows = FontFaceModel.objects.filter(deleted_at__isnull=True).only("id", "family", "variant", "file_reference")
        return [
            FontFace(
                family=row.family,
                variant=FontVariant(row.variant),
                source=FontSource.UPLOADED,
                reference=row.file_reference,
                # Unique per uploaded row, which is what makes it safe as a cache filename:
                # the file behind one row never changes.
                registered_name=f"vtu-{row.id.hex}",
            )
            for row in rows
        ]

    def remove(self, font_id: uuid.UUID) -> str | None:
        row = FontFaceModel.objects.filter(id=font_id, deleted_at__isnull=True).first()
        if row is None:
            return None
        now = timezone.now()
        FontFaceModel.objects.filter(pk=row.pk).update(deleted_at=now, updated_at=now, version=row.version + 1)
        return row.file_reference


class DjangoFontFileStore:
    """Concrete ``FontFileStore`` over Django storage."""

    def store(self, *, family: str, variant: FontVariant, data: bytes) -> str:
        # Keyed by family and variant so an operator can see what a file is, behind an
        # unguessable segment so the library cannot be enumerated by trying names.
        token = _unguessable("font", normalize_family(family), variant.value)
        key = f"diplomas/fonts/{token}/{normalize_family(family)}-{variant.value}.ttf"
        if default_storage.exists(key):
            default_storage.delete(key)
        default_storage.save(key, ContentFile(data))
        return f"{_MEDIA_PREFIX}{key}"

    def url_for(self, reference: str) -> str:
        """The reference is already the client-resolvable path every media field uses."""
        return reference
