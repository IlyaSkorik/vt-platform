"""What changes, and what must not, when uploads move to an S3 bucket.

The platform writes every file through ``default_storage`` and stores whatever that
storage calls the file's URL. That is one line of configuration away from an object store,
which is exactly the kind of claim that is worth pinning down: no network is needed to
check it, because minting a URL and deriving a key back from it are both local.

The bucket is public-read, so the confidentiality of a diploma rests entirely on its key
being unguessable. That is asserted here too.
"""

from __future__ import annotations

import uuid

import pytest
from django.core.files.storage import default_storage, storages
from django.test import override_settings

from apps.applications.presentation.api.v1.files import file_url
from apps.diplomas.infrastructure.pdf.workspace import _storage_key, _unguessable

#: A bucket that does not exist, reached through an endpoint that is never called: every
#: assertion below is about URLs and keys, which django-storages computes locally.
S3_STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": "vt-platform-media",
            "endpoint_url": "https://s3.example.test",
            "querystring_auth": False,
            "default_acl": None,
        },
    },
}


class TestReferencesFollowTheStorage:
    def test_a_local_reference_is_a_media_path(self) -> None:
        assert default_storage.url("competitions/1/poster.jpg") == "/media/competitions/1/poster.jpg"

    @override_settings(STORAGES=S3_STORAGES)
    def test_a_bucket_reference_is_an_absolute_url(self) -> None:
        storages._storages.pop("default", None)
        reference = default_storage.url("competitions/1/poster.jpg")
        assert reference.startswith("https://")
        assert reference.endswith("/competitions/1/poster.jpg")
        # No signature: the reference is stored in the database and has to keep working.
        assert "X-Amz-Signature" not in reference

    @override_settings(STORAGES=S3_STORAGES)
    def test_a_key_survives_the_round_trip_through_a_bucket_url(self) -> None:
        storages._storages.pop("default", None)
        key = "diplomas/documents/a/thank_you/tok/Петрова Ольга.pdf"
        assert _storage_key(default_storage.url(key)) == key

    def test_a_key_survives_the_round_trip_through_a_media_path(self) -> None:
        key = "diplomas/documents/a/thank_you/tok/Петрова Ольга.pdf"
        assert _storage_key(default_storage.url(key)) == key

    def teardown_method(self) -> None:
        # The override is gone; make the next reader of ``default_storage`` build it fresh.
        storages._storages.pop("default", None)


class TestAttachmentUrls:
    def test_an_opaque_key_becomes_a_url_at_the_edge(self) -> None:
        assert file_url("applications/attachments/x/track.mp3") == "/media/applications/attachments/x/track.mp3"

    def test_a_missing_file_stays_missing(self) -> None:
        assert file_url(None) is None
        assert file_url("   ") is None

    @pytest.mark.parametrize("reference", ["https://cdn.example.test/x.pdf", "/media/x.pdf"])
    def test_an_already_resolved_reference_passes_through(self, reference: str) -> None:
        """Otherwise a reference minted before the move would end up nested in a URL."""
        assert file_url(reference) == reference


class TestDiplomaKeysCannotBeGuessed:
    """A public-read bucket makes the key the only thing standing between a stranger and
    the whole diploma registry - and both parts of a diploma's natural key are public."""

    def test_the_token_depends_on_everything_it_is_given(self) -> None:
        competition = str(uuid.uuid4())
        first = _unguessable("print", competition, "VT-2026-000001")
        assert first != _unguessable("print", competition, "VT-2026-000002")
        assert first != _unguessable("print", str(uuid.uuid4()), "VT-2026-000001")
        assert first != _unguessable("print-zip", competition, "VT-2026-000001")

    def test_the_token_is_stable_so_regeneration_replaces_rather_than_orphans(self) -> None:
        competition = str(uuid.uuid4())
        assert _unguessable("print", competition, "VT-2026-000001") == _unguessable("print", competition, "VT-2026-000001")

    @override_settings(SECRET_KEY="a-different-secret")
    def test_the_token_is_not_derivable_without_the_secret(self) -> None:
        competition = str(uuid.uuid4())
        with override_settings(SECRET_KEY="the-original-secret"):
            original = _unguessable("print", competition, "VT-2026-000001")
        assert _unguessable("print", competition, "VT-2026-000001") != original
