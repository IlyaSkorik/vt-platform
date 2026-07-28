"""The diploma archive must not be resident in memory.

One archive holds every diploma of a competition, and every diploma is a full copy of the
template it was rendered over — so the archive's size tracks the tirage, not the page count.
A festival with 3 000 participants and a 2 MB template produces roughly 6 GB. Assembled in a
``BytesIO`` (as this once was, with a ``getvalue()`` copy on the end) that is ~12 GB of peak
memory, which no sensible server for this platform has.

Nothing about the result reveals how it was built, so the test measures instead: it zips more
content than it allows itself to allocate. `tracemalloc` counts Python-heap allocations,
which is exactly where a buffered archive would live.
"""

from __future__ import annotations

import os
import tracemalloc
import uuid
import zipfile

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace

pytestmark = pytest.mark.django_db

#: Twelve members of 1 MiB each: enough to overflow the 4 MiB spool several times over, and
#: enough that a buffered implementation could not hide inside the allowance below.
_MEMBERS = 12
_MEMBER_BYTES = 1024 * 1024

#: One chunk plus the spool threshold plus room for interpreter noise. Deliberately far
#: below the total content size - that gap is the whole assertion.
_PEAK_ALLOWANCE = 8 * 1024 * 1024


def _stored_documents(competition_id: uuid.UUID) -> list[tuple[str, str]]:
    """Write ``_MEMBERS`` incompressible files and return ``(arcname, reference)`` pairs."""
    items: list[tuple[str, str]] = []
    for index in range(_MEMBERS):
        # Genuinely random, because DEFLATE flattens anything with a repeating block and a
        # buffered archive of compressible bytes would stay small enough to pass.
        payload = os.urandom(_MEMBER_BYTES)
        key = f"diplomas/print/{competition_id}/member-{index}.pdf"
        if default_storage.exists(key):
            default_storage.delete(key)
        default_storage.save(key, ContentFile(payload))
        items.append((f"{index}.pdf", default_storage.url(key)))
    return items


class TestArchiveStreaming:
    def test_a_large_archive_is_streamed_rather_than_buffered(self) -> None:
        competition_id = uuid.uuid4()
        items = _stored_documents(competition_id)
        workspace = DjangoPrintPackageWorkspace()

        tracemalloc.start()
        try:
            reference = workspace.store_zip(competition_id=competition_id, items=items)
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        total = _MEMBERS * _MEMBER_BYTES
        assert peak < _PEAK_ALLOWANCE, (
            f"peaked at {peak / 1024 / 1024:.1f} MiB while archiving {total / 1024 / 1024:.0f} MiB - the archive is being held in memory again"
        )
        # And it is a real archive, not an empty file that trivially passes the above.
        with default_storage.open(_key(reference), "rb") as handle, zipfile.ZipFile(handle) as archive:
            assert sorted(archive.namelist()) == sorted(name for name, _ in items)
            assert len(archive.read("0.pdf")) == _MEMBER_BYTES

    def test_every_member_arrives_byte_for_byte(self) -> None:
        """Streaming is only worth anything if the contents survive it."""
        competition_id = uuid.uuid4()
        payload = b"%PDF-1.7 diploma bytes " * 500
        key = f"diplomas/print/{competition_id}/one.pdf"
        default_storage.save(key, ContentFile(payload))

        reference = DjangoPrintPackageWorkspace().store_zip(competition_id=competition_id, items=[("VT-2026-000001.pdf", default_storage.url(key))])

        with default_storage.open(_key(reference), "rb") as handle, zipfile.ZipFile(handle) as archive:
            assert archive.read("VT-2026-000001.pdf") == payload

    def test_a_missing_document_is_skipped_rather_than_failing_the_run(self) -> None:
        competition_id = uuid.uuid4()
        present = f"diplomas/print/{competition_id}/present.pdf"
        default_storage.save(present, ContentFile(b"%PDF-1.7 here"))

        reference = DjangoPrintPackageWorkspace().store_zip(
            competition_id=competition_id,
            items=[
                ("here.pdf", default_storage.url(present)),
                ("gone.pdf", default_storage.url(f"diplomas/print/{competition_id}/gone.pdf")),
            ],
        )

        with default_storage.open(_key(reference), "rb") as handle, zipfile.ZipFile(handle) as archive:
            assert archive.namelist() == ["here.pdf"]


def _key(reference: str) -> str:
    """The storage key behind a stored reference (a ``/media/…`` URL in tests)."""
    return reference.removeprefix("/media/")
