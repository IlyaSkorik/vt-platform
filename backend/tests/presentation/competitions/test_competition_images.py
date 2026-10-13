"""What happens to a picture between the upload form and storage.

These are the two promises ``apps.competitions.presentation.api.v1.images``
makes, and neither is visible from the outside once it is broken: a page that
is slow because it decodes twelve megapixels looks exactly like a page that is
slow for some other reason, and a stored photograph's GPS tag is invisible
until someone reads the file.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.competitions.presentation.api.v1.images import (
    LANDING_PIXELS,
    ImageRejectedError,
    store_image,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db


def _upload(image: Image.Image, *, fmt: str, exif: Image.Exif | None = None) -> SimpleUploadedFile:
    """Encode an in-memory image the way a browser would post it."""
    buffer = BytesIO()
    if exif is None:
        image.save(buffer, format=fmt)
    else:
        image.save(buffer, format=fmt, exif=exif)
    content_type = "image/jpeg" if fmt == "JPEG" else "image/png"
    suffix = "jpg" if fmt == "JPEG" else "png"
    return SimpleUploadedFile(f"upload.{suffix}", buffer.getvalue(), content_type=content_type)


def _stored(url: str) -> Image.Image:
    """Re-open what landed in storage, given the URL the endpoint returned."""
    relative = url.removeprefix("/media/")
    with default_storage.open(relative) as handle:
        return Image.open(BytesIO(handle.read()))


def test_a_phone_photograph_is_scaled_down_turned_upright_and_stripped(tmp_path: Path, settings: SettingsWrapper) -> None:
    """The three things the re-encode exists for, on one file.

    A 4000×3000 portrait held sideways with an orientation tag is what actually
    arrives from a phone. Stored as-is it is a twelve-megapixel decode into a
    287px box, it is displayed on its side, and it carries wherever it was taken.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    exif = Image.Exif()
    exif[274] = 6  # Orientation: rotate 90° — what a phone writes instead of rotating pixels.
    exif[0x9286] = "shot at home"  # UserComment stands in for the GPS block: same question.
    source = Image.new("RGB", (4000, 3000), (120, 80, 160))

    url = store_image(
        uploaded=_upload(source, fmt="JPEG", exif=exif),
        key_prefix="competitions/x/landing",
        max_edge=LANDING_PIXELS,
    )

    stored = _stored(url)
    # Scaled to fit the box, aspect ratio intact.
    assert max(stored.size) == LANDING_PIXELS
    # Turned upright: the tag said 90°, so the stored pixels are portrait.
    assert stored.height > stored.width
    # And nothing of the original's metadata came with it.
    assert len(stored.getexif()) == 0


def test_a_transparent_logo_stays_transparent(tmp_path: Path, settings: SettingsWrapper) -> None:
    """A partner's logo is routinely a PNG with no background.

    Flattening it onto white — which is what the avatar pipeline does, because an
    avatar is always JPEG — looks right until the dark theme is switched on and
    every logo sits in a white box.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    source = Image.new("RGBA", (2400, 2400), (255, 0, 0, 0))

    url = store_image(
        uploaded=_upload(source, fmt="PNG"),
        key_prefix="competitions/x/landing",
        max_edge=LANDING_PIXELS,
    )

    assert url.endswith(".png")
    assert _stored(url).mode == "RGBA"


def test_a_small_logo_is_left_at_its_own_size(tmp_path: Path, settings: SettingsWrapper) -> None:
    """Scaled down, never up: a 300px logo blown up to 1600 is a blurry 300px logo."""
    settings.MEDIA_ROOT = str(tmp_path)
    source = Image.new("RGB", (300, 120), (10, 10, 10))

    url = store_image(
        uploaded=_upload(source, fmt="JPEG"),
        key_prefix="competitions/x/landing",
        max_edge=LANDING_PIXELS,
    )

    assert _stored(url).size == (300, 120)


def test_a_file_that_is_not_an_image_is_refused(tmp_path: Path, settings: SettingsWrapper) -> None:
    """The round trip is the check: a PDF renamed to .jpg cannot survive a decode.

    Better than trusting the ``Content-Type`` the browser announced, which is
    whatever the client chose to send.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    not_an_image = SimpleUploadedFile("photo.jpg", b"%PDF-1.7 not really", content_type="image/jpeg")

    with pytest.raises(ImageRejectedError):
        store_image(
            uploaded=not_an_image,
            key_prefix="competitions/x/landing",
            max_edge=LANDING_PIXELS,
        )
