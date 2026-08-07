"""Participant avatars: accept an image, normalise it, store it as a file.

Before this existed the client read the picked image with ``FileReader`` and sent
the base64 ``data:`` URL as the ``avatarUrl`` *string*, so every avatar was stored
inline in a Postgres text column. That is wrong in three separate ways, and only
the first is about tidiness:

* Base64 costs a third on top of the bytes, and the registry's list endpoint
  returns ``avatarUrl`` for every row — a thousand participants with photographs
  is hundreds of megabytes of JSON for one screen, on every load, uncacheable
  because a ``data:`` URL is part of the response rather than a resource beside it.
* Every database backup carries the photographs.
* **A phone photograph carries EXIF, and EXIF carries GPS.** These are pictures of
  children. Storing the file exactly as the camera wrote it means storing where it
  was taken, and nothing downstream ever strips it.

So the image is re-encoded rather than merely copied: decoded, rotated upright
from its EXIF orientation, cropped square, resized to :data:`_AVATAR_PIXELS` and
written back out as JPEG. Re-encoding is what makes the metadata go away — and it
also means a file that is not really an image cannot survive the round trip, which
is a better defence than trusting the ``Content-Type`` the browser announced.

The endpoint is deliberately *not* scoped to a participant id: the registry form
picks an avatar before the participant exists. It stores the file, returns its
URL, and the create/update payload carries that URL like any other reference.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps, UnidentifiedImageError

__all__ = [
    "ACCEPTED_CONTENT_TYPES",
    "MAX_UPLOAD_BYTES",
    "AvatarRejectedError",
    "store_avatar",
]

#: What the picker is allowed to hand over. The list is the browser-supported
#: still-image formats; everything else (HEIC from an iPhone straight out of the
#: camera, say) the client converts or the user re-saves.
ACCEPTED_CONTENT_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})

#: Ceiling on the *upload*, not on what is stored — the stored file is a 512 px
#: JPEG and lands around 40 KB whatever arrives. Generous enough for a photo
#: straight off a phone, small enough that a mistake is not a denial of service.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

#: Edge of the stored square. An avatar is drawn at 40–96 px in the registry and
#: at most a couple of hundred on a profile; 512 covers a retina profile view with
#: room to spare and is far below what any phone camera produces.
_AVATAR_PIXELS = 512

#: JPEG quality. 85 is the usual point where the next quality step costs more
#: bytes than it returns in visible difference at this size.
_JPEG_QUALITY = 85

#: Guards against a decompression bomb: a small file that expands to a gigantic
#: bitmap. Pillow warns past its own default; this refuses outright.
_MAX_PIXELS = 50_000_000


class AvatarRejectedError(Exception):
    """The upload cannot become an avatar. Carries the message the user sees."""


def store_avatar(*, uploaded: Any, owner_id: uuid.UUID) -> str:
    """Normalise an uploaded image and store it. Returns the stored file's URL.

    Raises :class:`AvatarRejectedError` with a message meant for the person who picked
    the file — every refusal here is something they can act on.
    """
    if uploaded is None:
        raise AvatarRejectedError("Выберите изображение.")

    content_type = str(getattr(uploaded, "content_type", "") or "").lower()
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise AvatarRejectedError("Допустимы только JPEG, PNG или WebP.")

    if getattr(uploaded, "size", 0) > MAX_UPLOAD_BYTES:
        raise AvatarRejectedError("Размер файла не должен превышать 8 МБ.")

    data = _normalise(uploaded)
    key = f"participants/avatars/{owner_id}/{uuid.uuid4().hex}.jpg"
    stored = default_storage.save(key, ContentFile(data))
    # Ask the storage for the URL rather than assembling one: that single call is
    # what decides whether this lives under /media/ or in a bucket.
    return default_storage.url(stored)


def _normalise(uploaded: Any) -> bytes:
    """Decode, strip metadata, square off, resize, re-encode as JPEG."""
    try:
        with Image.open(uploaded) as image:
            # Before anything else: a file that decodes to an implausible bitmap is
            # refused rather than resized, so a 10 KB upload cannot ask for gigabytes.
            width, height = image.size
            if width * height > _MAX_PIXELS:
                raise AvatarRejectedError("Изображение слишком большое по количеству пикселей.")

            # Phones record orientation in EXIF rather than rotating the pixels, so
            # without this a portrait photo is stored on its side — and the tag that
            # said so is about to be discarded.
            upright = ImageOps.exif_transpose(image) or image
            # Flattened onto white: the output is JPEG, which has no alpha, and
            # compositing beats letting a transparent PNG come out with black edges.
            if upright.mode in {"RGBA", "LA", "P"}:
                converted = upright.convert("RGBA")
                canvas = Image.new("RGB", converted.size, (255, 255, 255))
                canvas.paste(converted, mask=converted.split()[-1])
                upright = canvas
            elif upright.mode != "RGB":
                upright = upright.convert("RGB")

            # Centre-cropped to a square rather than letterboxed: an avatar is drawn
            # in a circle, and a fitted rectangle would show as bars inside it.
            square = ImageOps.fit(upright, (_AVATAR_PIXELS, _AVATAR_PIXELS), method=Image.Resampling.LANCZOS)

            buffer = BytesIO()
            # No `exif=` argument, which is the point: nothing from the original
            # file's metadata is carried into the copy that gets stored.
            square.save(buffer, format="JPEG", quality=_JPEG_QUALITY, optimize=True, progressive=True)
            return buffer.getvalue()
    except AvatarRejectedError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Covers a truncated file, a mislabelled one, and anything Pillow cannot
        # make sense of — all the same thing to the person who picked it.
        raise AvatarRejectedError("Не удалось прочитать изображение. Попробуйте другой файл.") from exc
