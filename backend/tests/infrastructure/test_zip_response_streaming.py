"""``zip_response`` must send the archive while it builds it, not after.

This is a latency property, and the only one that matters here. The first version of
this spooled the whole ZIP to disk before answering: memory stayed bounded, but a
festival's backing tracks are several hundred objects read out of a bucket, and every
proxy in between saw silence for as long as that took. nginx answers 504 for an upstream
that has said nothing for ``proxy_read_timeout``, and the backend then finishes an
archive nobody is waiting for any more — which is exactly what «архив не скачивается»
was.

The second version streamed, and still did not, because it handed Django a *sync*
generator: ``StreamingHttpResponse.__aiter__`` collects one of those into a list before
yielding, so under ASGI the archive went into the heap in full and the worker died under
a video archive — headers sent, then ``ERR_INCOMPLETE_CHUNKED_ENCODING``. Hence
:func:`test_the_response_is_async_so_asgi_cannot_buffer_it`: it is the one assertion
that distinguishes a response that streams from one that merely looks like it does.

Nothing about the finished file reveals how it was produced, so these measure instead.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import aclosing
from typing import IO, Any

import pytest
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from config.archive import ArchiveMember, zip_response

pytestmark = pytest.mark.django_db


def _body(response: Any) -> bytes:
    """The whole response body.

    Iterating the *response* rather than ``streaming_content``: Django adapts an async
    body for a synchronous caller, and reaching past the response for its internals is
    what let a buffered implementation pass this file once already.
    """
    return b"".join(response)


def _first_chunk(response: Any) -> bytes:
    """Only the first chunk, leaving the rest of the archive unbuilt."""

    async def pull() -> bytes:
        async with aclosing(aiter(response)) as body:
            async for chunk in body:
                return bytes(chunk)
        return b""

    return async_to_sync(pull)()


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
    def test_the_response_is_async_so_asgi_cannot_buffer_it(self, stored: list[ArchiveMember]) -> None:
        response = zip_response(stored, filename="фонограммы.zip")

        assert response.is_async, (
            "the body is a sync iterator: StreamingHttpResponse.__aiter__ collects one "
            "into a list before sending a byte, so under ASGI the whole archive sits in "
            "memory and nothing here streams"
        )

    def test_the_first_bytes_go_out_before_the_last_file_is_read(self, stored: list[ArchiveMember], monkeypatch: pytest.MonkeyPatch) -> None:
        opened: list[str] = []
        real_open = default_storage.open

        def recording_open(key: str, mode: str = "rb") -> IO[bytes]:
            opened.append(key)
            return real_open(key, mode)

        monkeypatch.setattr(default_storage, "open", recording_open)

        first = _first_chunk(zip_response(stored, filename="фонограммы.zip"))

        assert first, "the response yielded nothing at all before blocking"
        # The assertion: the client has bytes while most of the bucket is still unread.
        assert len(opened) < _MEMBERS, (
            f"every one of {_MEMBERS} members was read before a single byte was sent — the archive is being assembled up front again"
        )

    def test_what_comes_out_is_a_readable_archive(self, stored: list[ArchiveMember]) -> None:
        # Streaming writes each entry's size into a trailing data descriptor instead of
        # patching its header, so "it streams" and "unzip can open it" are two facts.
        response = zip_response(stored, filename="фонограммы.zip", notes=["Без фонограммы: 09"])

        with zipfile.ZipFile(io.BytesIO(_body(response))) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [f"{index:02d}.mp3" for index in range(_MEMBERS)] + ["ПРОЧТИ.txt"]
            assert len(archive.read("00.mp3")) == _MEMBER_BYTES
            assert "Без фонограммы: 09" in archive.read("ПРОЧТИ.txt").decode()

    def test_the_download_is_never_served_from_the_browser_cache(self, stored: list[ArchiveMember]) -> None:
        # Assembled per request from whatever is stored now, at a URL that never changes.
        # Reusing a stored copy means handing back the archive from before the diplomas
        # were re-issued, and nothing in the URL would ever say otherwise.
        response = zip_response(stored, filename="фонограммы.zip")

        assert response["Cache-Control"] == "no-store"

    def test_a_missing_file_costs_its_own_entry_and_nothing_else(self, stored: list[ArchiveMember]) -> None:
        members = [*stored, ArchiveMember(arcname="99.mp3", reference="nothing/here.mp3")]

        with zipfile.ZipFile(io.BytesIO(_body(zip_response(members, filename="ф.zip")))) as archive:
            assert "99.mp3" not in archive.namelist()
            assert len(archive.namelist()) == _MEMBERS + 1  # the others, plus the notes
            assert "Файл не найден в хранилище: 99.mp3" in archive.read("ПРОЧТИ.txt").decode()
