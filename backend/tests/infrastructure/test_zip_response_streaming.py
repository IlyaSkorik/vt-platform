"""``zip_response`` must send the archive while it builds it, not after.

This is a latency property, and the only one that matters here. The previous
implementation spooled the whole ZIP to disk before answering: memory stayed bounded,
but a festival's backing tracks are several hundred objects read out of a bucket, and
every proxy in between saw silence for as long as that took. nginx answers 504 for an
upstream that has said nothing for ``proxy_read_timeout``, and the backend then finishes
an archive nobody is waiting for any more — which is exactly what «архив не
скачивается» was.

Nothing about the finished file reveals how it was produced, so the test measures the
one thing that does: how much of the work has happened by the time the first bytes are
out.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from collections.abc import Iterator
from typing import IO, Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from config.archive import ArchiveMember, zip_response

pytestmark = pytest.mark.django_db


def _chunks(response: Any) -> Iterator[bytes]:
    """The response body, chunk by chunk.

    ``streaming_content`` is typed as "sync or async iterator"; these responses are
    always the sync one, and saying so here keeps the tests readable.
    """
    return iter(response.streaming_content)


#: Enough members that "streamed" and "assembled first" are far apart.
_MEMBERS = 8
_MEMBER_BYTES = 128 * 1024


@pytest.fixture
def stored() -> Iterator[list[ArchiveMember]]:
    prefix = f"test-archives/{uuid.uuid4()}"
    members = []
    for index in range(_MEMBERS):
        key = f"{prefix}/track-{index}.mp3"
        default_storage.save(key, ContentFile(b"\0" * _MEMBER_BYTES))
        members.append(ArchiveMember(arcname=f"{index:02d}.mp3", reference=key))
    yield members
    for member in members:
        default_storage.delete(member.reference)


class TestZipStreaming:
    def test_the_first_bytes_go_out_before_the_last_file_is_read(self, stored: list[ArchiveMember], monkeypatch: pytest.MonkeyPatch) -> None:
        opened: list[str] = []
        real_open = default_storage.open

        def recording_open(key: str, mode: str = "rb") -> IO[bytes]:
            opened.append(key)
            return real_open(key, mode)

        monkeypatch.setattr(default_storage, "open", recording_open)

        response = zip_response(stored, filename="фонограммы.zip")
        first = next(_chunks(response))

        assert first, "the response yielded nothing at all before blocking"
        # The assertion: the client has bytes while most of the bucket is still unread.
        assert len(opened) < _MEMBERS, (
            f"every one of {_MEMBERS} members was read before a single byte was sent — the archive is being assembled up front again"
        )

    def test_what_comes_out_is_a_readable_archive(self, stored: list[ArchiveMember]) -> None:
        # Streaming writes each entry's size into a trailing data descriptor instead of
        # patching its header, so "it streams" and "unzip can open it" are two facts.
        response = zip_response(stored, filename="фонограммы.zip", notes=["Без фонограммы: 09"])

        blob = b"".join(_chunks(response))
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [f"{index:02d}.mp3" for index in range(_MEMBERS)] + ["ПРОЧТИ.txt"]
            assert len(archive.read("00.mp3")) == _MEMBER_BYTES
            assert "Без фонограммы: 09" in archive.read("ПРОЧТИ.txt").decode()

    def test_a_missing_file_costs_its_own_entry_and_nothing_else(self, stored: list[ArchiveMember]) -> None:
        members = [*stored, ArchiveMember(arcname="99.mp3", reference="nothing/here.mp3")]

        blob = b"".join(_chunks(zip_response(members, filename="ф.zip")))
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            assert "99.mp3" not in archive.namelist()
            assert len(archive.namelist()) == _MEMBERS + 1  # the others, plus the notes
            assert "Файл не найден в хранилище: 99.mp3" in archive.read("ПРОЧТИ.txt").decode()
