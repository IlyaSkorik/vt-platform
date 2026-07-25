"""``DjangoPrintPackageWorkspace`` — the infra side of print-package generation.

Loads a template's fields and backing PDF, renders diploma PDFs (reportlab/pypdf),
and stores the per-diploma PDFs and the final ZIP in ``default_storage`` under
``/media/…`` paths (served directly, as every other upload in this codebase).
"""

from __future__ import annotations

import io
import uuid
import zipfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.diplomas.application.interfaces import TemplateAssets
from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.models import TemplateDocumentModel
from apps.diplomas.infrastructure.pdf.qr import verification_url
from apps.diplomas.infrastructure.pdf.renderer import render_diploma_pdf
from apps.diplomas.presentation.api.v1.diplomas import composition

__all__ = ["DjangoPrintPackageWorkspace"]


def _storage_key(media_path: str) -> str:
    """Strip a leading ``/media/`` from a stored reference to a storage key."""
    prefix = f"/{settings.MEDIA_URL.strip('/')}/"
    return media_path[len(prefix) :] if media_path.startswith(prefix) else media_path.lstrip("/")


def _media_path(key: str) -> str:
    return f"/{settings.MEDIA_URL.strip('/')}/{key}"


class DjangoPrintPackageWorkspace:
    """Concrete ``PrintPackageWorkspace`` over Django storage + the PDF renderer."""

    def load_template(self, template_id: uuid.UUID) -> TemplateAssets | None:
        document = (
            TemplateDocumentModel.objects.filter(template__id=template_id, deleted_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if document is None:
            return None
        key = _storage_key(document.file_reference)
        if not default_storage.exists(key):
            return None
        with default_storage.open(key, "rb") as handle:
            backing_pdf = handle.read()
        layout = composition.get_template_layout(str(template_id))
        return TemplateAssets(fields=list(layout["fields"]), backing_pdf=backing_pdf)

    def render(
        self,
        *,
        assets: TemplateAssets,
        snapshot: DiplomaSnapshot,
        number: str,
        verification_token: str,
    ) -> bytes:
        # The public verification domain is configuration, so the URL is built here
        # (infrastructure) rather than passed down from the application service.
        return render_diploma_pdf(
            fields=assets.fields,
            backing_pdf=assets.backing_pdf,
            snapshot=snapshot,
            number=number,
            verification_url=verification_url(verification_token),
        )

    def store_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        key = f"diplomas/print/{competition_id}/{number}.pdf"
        if default_storage.exists(key):
            default_storage.delete(key)
        default_storage.save(key, ContentFile(data))
        return _media_path(key)

    def store_zip(self, *, competition_id: uuid.UUID, items: list[tuple[str, str]]) -> str:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for arcname, media_path in items:
                key = _storage_key(media_path)
                if not default_storage.exists(key):
                    continue
                with default_storage.open(key, "rb") as handle:
                    archive.writestr(arcname, handle.read())
        key = f"diplomas/print/{competition_id}/Diplomas.zip"
        if default_storage.exists(key):
            default_storage.delete(key)
        default_storage.save(key, ContentFile(buffer.getvalue()))
        return _media_path(key)
