"""Competition imagery: accept an upload, normalise it, store it as a file.

Both image endpoints on a competition — the poster and the landing builder's
pictures — used to hand the uploaded file straight to storage, up to 5 MB,
exactly as the camera wrote it. That is wrong in two separate ways, and only
the first one is visible:

* **The page decodes what was uploaded.** Nothing resizes these, and nothing
  serves a smaller variant, so a jury portrait shot on a phone arrives as
  4000×3000 and the browser decodes twelve megapixels — some 48 MB of bitmap,
  tens of milliseconds of the main thread — to paint it into a 287×276 box.
  Three of those on a screen is a carousel that visibly stutters the first time
  it moves, and the stutter is the decode, not the scrolling.
* **A phone photograph carries EXIF, and EXIF carries GPS.** These are
  pictures of children at festivals. Storing the file byte for byte means
  storing where it was taken, and nothing downstream ever strips it.

So the image is re-encoded rather than copied: decoded, turned upright from its
EXIF orientation, scaled down to fit a sensible box and written back out. The
re-encode is what makes the metadata go away — and it also means a file that is
not really an image cannot survive the round trip, which is a better defence
than trusting the ``Content-Type`` the browser announced.

This is the same treatment participant avatars already get (see
``participants/presentation/api/v1/registry/avatars.py``) with two differences,
both of which come from what the pictures are for. An avatar is drawn in a
circle, so it is centre-cropped square; these are posters, portraits and logos
shown at their own proportions, so they are only ever scaled down — never
cropped and never enlarged. And an avatar is always JPEG, while a partner's
logo is routinely a PNG with a transparent background, which flattening onto
white would ruin the moment the dark theme is switched on. So transparency
decides the output format, not the input's.
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
    "LANDING_PIXELS",
    "MAX_UPLOAD_BYTES",
    "POSTER_PIXELS",
    "ImageRejectedError",
    "store_image",
]

#: What the picker is allowed to hand over — the browser-supported still-image
#: formats. Anything else (HEIC straight off an iPhone, say) is converted by the
#: client or re-saved by the user.
ACCEPTED_CONTENT_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})

#: Ceiling on the *upload*, not on what is stored: whatever arrives, the stored
#: file is bounded by the box below. Generous enough for a photo off a phone,
#: small enough that a mistake is not a denial of service.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

#: Longest edge of a stored poster. The afisha runs the full width of the
#: landing (1293 px in the frame), so this is a retina-ish 1.6× of that rather
#: than a round number — past it the extra pixels are never sampled.
POSTER_PIXELS = 2048

#: Longest edge of a stored landing picture. The largest box any of them is
#: drawn in is the gallery's 291×221 and the jury's 287×276, so 1600 leaves room
#: for a lightbox at full screen and for whatever the design does next.
LANDING_PIXELS = 1600

#: JPEG quality. 85 is the usual point where the next step costs more bytes than
#: it returns in visible difference.
_JPEG_QUALITY = 85

#: Guards against a decompression bomb: a small file that expands to a gigantic
#: bitmap. Pillow warns past its own default; this refuses outright.
_MAX_PIXELS = 50_000_000

#: Modes that carry an alpha channel, and therefore have to stay PNG.
_ALPHA_MODES = frozenset({"RGBA", "LA", "PA"})


class ImageRejectedError(Exception):
    """The upload cannot become an image. Carries the message the user sees."""


def store_image(*, uploaded: Any, key_prefix: str, max_edge: int) -> str:
    """Normalise an uploaded image and store it. Returns the stored file's URL.

    ``key_prefix`` is the folder the file lands in; the name within it is always
    a fresh uuid. Never a fixed name: a bucket overwrites a repeated key in
    place and serves it back ``immutable`` for a year, so replacing a poster
    would leave both the stored reference and every cached copy on the old one.

    Raises :class:`ImageRejectedError` with a message meant for the person who
    picked the file — every refusal here is something they can act on.
    """
    if uploaded is None:
        raise ImageRejectedError("Выберите изображение.")

    content_type = str(getattr(uploaded, "content_type", "") or "").lower()
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise ImageRejectedError("Допустимы только JPEG, PNG или WebP.")

    if getattr(uploaded, "size", 0) > MAX_UPLOAD_BYTES:
        raise ImageRejectedError("Размер файла не должен превышать 5 МБ.")

    data, extension = _normalise(uploaded, max_edge=max_edge)
    stored = default_storage.save(f"{key_prefix}/{uuid.uuid4().hex}{extension}", ContentFile(data))
    # Ask the storage for the URL rather than assembling one: that single call is
    # what decides whether this lives under /media/ or in a bucket.
    return default_storage.url(stored)


def _normalise(uploaded: Any, *, max_edge: int) -> tuple[bytes, str]:
    """Decode, strip metadata, scale down to fit, re-encode. Returns bytes and extension."""
    try:
        with Image.open(uploaded) as image:
            # Before anything else: a file that decodes to an implausible bitmap
            # is refused rather than resized, so a 10 KB upload cannot ask for
            # gigabytes of memory.
            width, height = image.size
            if width * height > _MAX_PIXELS:
                raise ImageRejectedError("Изображение слишком большое по количеству пикселей.")

            # Phones record orientation in EXIF rather than rotating the pixels,
            # so without this a portrait photo is stored on its side — and the
            # tag that said so is about to be discarded.
            upright = ImageOps.exif_transpose(image) or image

            keeps_alpha = upright.mode in _ALPHA_MODES or (upright.mode == "P" and "transparency" in upright.info)
            upright = upright.convert("RGBA" if keeps_alpha else "RGB")

            # `thumbnail` is the whole reason this is not `ImageOps.fit`: it
            # scales down in place, preserves the aspect ratio, and leaves an
            # image that is already smaller than the box completely alone. A
            # logo authored at 300 px must not be blown up to 1600.
            upright.thumbnail((max_edge, max_edge), resample=Image.Resampling.LANCZOS)

            buffer = BytesIO()
            # No `exif=` argument anywhere below, which is the point: nothing
            # from the original file's metadata reaches the copy that is stored.
            if keeps_alpha:
                upright.save(buffer, format="PNG", optimize=True)
                return buffer.getvalue(), ".png"
            upright.save(
                buffer,
                format="JPEG",
                quality=_JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
            return buffer.getvalue(), ".jpg"
    except ImageRejectedError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Covers a truncated file, a mislabelled one, and anything Pillow cannot
        # make sense of — all the same thing to the person who picked it.
        raise ImageRejectedError("Не удалось прочитать изображение. Попробуйте другой файл.") from exc
