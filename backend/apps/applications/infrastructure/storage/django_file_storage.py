"""``DjangoFileStorage`` - the ``FileStorage`` adapter over Django's storage backend.

Persists uploaded attachment bytes through Django's configured ``default_storage``
(local media in development, an object store in production) and returns the saved
key as the opaque reference the aggregate stores in a ``FileReference``. The domain
never learns whether that key is a filesystem path or an object-store key.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename

from apps.applications.infrastructure.models.base import uuid7

__all__ = ["DjangoFileStorage"]

_ATTACHMENT_PREFIX = "applications/attachments"


class DjangoFileStorage:
    """Store/delete attachment bytes via Django's ``default_storage``."""

    def save(self, *, content: bytes, filename: str, content_type: str) -> str:
        """Store ``content`` under a unique key and return that key."""
        safe_name = get_valid_filename(PurePosixPath(filename).name) or "upload"
        key = f"{_ATTACHMENT_PREFIX}/{uuid7()}/{safe_name}"
        return default_storage.save(key, ContentFile(content))

    def delete(self, *, reference: str) -> None:
        """Delete the stored object at ``reference`` (best-effort; ignores absence)."""
        if default_storage.exists(reference):
            default_storage.delete(reference)
