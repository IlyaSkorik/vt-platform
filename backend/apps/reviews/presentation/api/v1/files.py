"""Storing a review's photographs, and turning them back into addresses.

Both halves live at the edge on purpose. The size cap, the accepted media types
and the storage key are HTTP-and-bucket facts; a use case that knew them would be
a use case that has to be mocked to test a sentence of text (see the note in
``application/interfaces.py``).

The upload is the one place in this context where a stranger with no account
writes bytes to the platform's storage, so it refuses more than it accepts:
images only, by what the file *is* rather than by what it is called, and a
per-file ceiling far below what a photograph from a phone needs.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from django.core.files.storage import default_storage

__all__ = ["PHOTO_MAX_BYTES", "PhotoRejectedError", "photo_url", "store_photo"]

#: What a photograph may weigh. A phone's own share-sized JPEG is well under this;
#: anything above is either a raw export or not a photograph at all.
PHOTO_MAX_BYTES: Final = 8 * 1024 * 1024

_EXTENSION_BY_TYPE: Final[dict[str, str]] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    # Phones hand these over by default now, and a visitor should not have to know
    # that to leave a photograph.
    "image/heic": ".heic",
    "image/heif": ".heif",
}


class PhotoRejectedError(ValueError):
    """The upload is not something this endpoint will keep.

    Carries the Russian sentence the visitor sees; the caller renders it as a
    validation problem rather than guessing at its own wording.
    """


def store_photo(uploaded: Any, *, slug: str) -> str:
    """Write one uploaded photograph and return its storage reference.

    Keyed by the page's slug rather than by the review's id: the file is written
    before the review exists, and inventing an id here only to discover the note
    itself is refused would leave orphans named after rows that never appeared.
    """
    content_type = str(getattr(uploaded, "content_type", "") or "").lower().split(";")[0].strip()
    extension = _EXTENSION_BY_TYPE.get(content_type)
    if extension is None:
        raise PhotoRejectedError("Фотографии принимаются в форматах JPEG, PNG, WebP или HEIC.")
    if int(getattr(uploaded, "size", 0) or 0) > PHOTO_MAX_BYTES:
        raise PhotoRejectedError(f"Каждая фотография — не больше {PHOTO_MAX_BYTES // (1024 * 1024)} МБ.")
    # A fresh key every time, never anything derived from the uploaded name: the
    # name arrives from a stranger, and a bucket overwrites a repeated key in place.
    return default_storage.save(f"reviews/{slug}/{uuid.uuid4().hex}{extension}", uploaded)


def photo_url(reference: str | None) -> str | None:
    """The address a stored photograph is reachable at, or ``None``.

    Idempotent for anything already absolute, exactly as the applications edge
    does it: a reference the storage hands back whole passes through rather than
    being nested inside a second URL.
    """
    key = (reference or "").strip()
    if not key:
        return None
    if key.startswith(("http://", "https://", "/")):
        return key
    return default_storage.url(key)
