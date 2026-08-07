"""REST tests for the participant avatar upload.

The endpoint exists because the picture used to be sent as a base64 ``data:`` URL
and stored inline in a text column. So what these pin down is not "an upload
works" but the three things that made that wrong: the image becomes a *file* in
storage, it is re-encoded rather than kept as it arrived (which is what removes
the EXIF a phone photograph of a child carries), and the write field no longer
accepts the old inline form.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image
from rest_framework.test import APIClient

from apps.identity.presentation.api.v1.auth import composition

pytestmark = pytest.mark.django_db

AVATAR_URL = "/api/v1/participants/registry/avatar"
_PASSWORD = "Str0ngPass!word"


def storage_key_of_url(url: str) -> str:
    """The storage key behind a returned URL.

    The suite runs on the filesystem backend, where a URL is ``MEDIA_URL`` plus the
    key — so this is the inverse of what the endpoint called to build it. A bucket
    would return an absolute URL instead, which is exactly the difference these
    tests do not need to care about.
    """
    return url.removeprefix(settings.MEDIA_URL).lstrip("/")


@pytest.fixture(autouse=True)
def _media_root(settings: Any, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def auth_client() -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "avatar-guardian@example.com", "password": _PASSWORD, "firstName": "Olga", "lastName": "Petrova"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = str(composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _image(
    *,
    size: tuple[int, int] = (900, 600),
    fmt: str = "JPEG",
    mode: str = "RGB",
    exif: bytes | None = None,
) -> bytes:
    image = Image.new(mode, size, (200, 30, 30) if mode == "RGB" else (200, 30, 30, 128))
    buffer = io.BytesIO()
    if exif is not None:
        image.save(buffer, format=fmt, exif=exif)
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


def _upload(client: APIClient, content: bytes, *, name: str = "avatar.jpg", content_type: str = "image/jpeg") -> Any:
    from django.core.files.uploadedfile import SimpleUploadedFile

    return client.post(AVATAR_URL, {"file": SimpleUploadedFile(name, content, content_type=content_type)}, format="multipart")


def test_the_avatar_becomes_a_stored_file_not_a_string(auth_client: APIClient) -> None:
    response = _upload(auth_client, _image())

    assert response.status_code == 201, response.data
    url = response.data["data"]["url"]
    # The whole point: a reference to something in storage, never the image inline.
    assert not url.startswith("data:")
    assert default_storage.exists(storage_key_of_url(url))


def test_the_stored_image_is_a_square_of_the_expected_size(auth_client: APIClient) -> None:
    """A phone photo is 4000 px; the registry draws avatars at 40. Re-encode or the
    list screen downloads megabytes per row."""
    response = _upload(auth_client, _image(size=(2400, 1600)))

    stored = default_storage.open(storage_key_of_url(response.data["data"]["url"]), "rb").read()
    with Image.open(io.BytesIO(stored)) as image:
        assert image.size == (512, 512)
        assert image.format == "JPEG"
    assert len(stored) < 200_000


def test_exif_does_not_survive_the_upload(auth_client: APIClient) -> None:
    """These are photographs of children, and EXIF carries GPS."""
    exif = Image.Exif()
    exif[0x010E] = "taken somewhere private"  # ImageDescription — stands in for any tag
    original = _image(exif=exif.tobytes())
    with Image.open(io.BytesIO(original)) as check:
        assert check.getexif(), "the fixture must actually carry EXIF, or this proves nothing"

    response = _upload(auth_client, original)

    stored = default_storage.open(storage_key_of_url(response.data["data"]["url"]), "rb").read()
    with Image.open(io.BytesIO(stored)) as image:
        assert not dict(image.getexif())


def test_a_transparent_png_is_flattened_rather_than_blackened(auth_client: APIClient) -> None:
    response = _upload(auth_client, _image(fmt="PNG", mode="RGBA"), name="a.png", content_type="image/png")

    assert response.status_code == 201, response.data
    stored = default_storage.open(storage_key_of_url(response.data["data"]["url"]), "rb").read()
    with Image.open(io.BytesIO(stored)) as image:
        assert image.mode == "RGB"


def test_a_file_that_is_not_an_image_is_refused(auth_client: APIClient) -> None:
    """The declared content type is the client's word for it; the decode is the check."""
    response = _upload(auth_client, b"%PDF-1.4\nnot an image at all\n")

    assert response.status_code == 400
    assert "изображение" in str(response.data).lower()


def test_an_unsupported_format_is_refused_by_name(auth_client: APIClient) -> None:
    response = _upload(auth_client, _image(), name="a.gif", content_type="image/gif")

    assert response.status_code == 400
    assert "JPEG" in str(response.data)


def test_anonymous_callers_cannot_upload(auth_client: APIClient) -> None:
    """Otherwise the endpoint is public image hosting on someone else's bucket."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    response = APIClient().post(
        AVATAR_URL,
        {"file": SimpleUploadedFile("a.jpg", _image(), content_type="image/jpeg")},
        format="multipart",
    )

    assert response.status_code == 401


def test_the_registry_no_longer_accepts_an_inline_image(auth_client: APIClient) -> None:
    """The route that produced the problem is closed, not merely unused by our client."""
    inline = "data:image/png;base64," + ("A" * 4000)

    response = auth_client.post(
        "/api/v1/participants/registry",
        {
            "participantType": "solo",
            "firstName": "Мария",
            "lastName": "Иванова",
            "birthDate": "2015-04-01",
            "gender": "female",
            "avatarUrl": inline,
            "organizations": [],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "avatarUrl" in str(response.data)
