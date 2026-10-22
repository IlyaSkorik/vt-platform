"""Streaming a set of stored files out of an endpoint as one ZIP download.

A technical helper, not a bounded context: it knows about storage and HTTP and
nothing else, which is why it sits beside :mod:`config.middleware` rather than
inside any one app. Three edges compose archives out of the same stored files —
the programme's backing tracks, its video material and the organizer's
paperwork — and none of them should own the others' copy of this.

**The archive is written as it is sent, not assembled and then sent.** That is
the load-bearing decision here, and it is about *latency*, not memory. This used
to spool the whole ZIP to disk first, which bounded memory but meant the client —
and every proxy in between — saw nothing at all until the last file had been read
out of the bucket. A festival's backing tracks are several hundred objects, and
that silence runs into minutes; nginx gives up on an upstream that has said
nothing for ``proxy_read_timeout`` and answers 504, after which the backend
finishes the archive and throws it away. Raising that limit only moves the number
the next festival has to stay under. Bytes that flow continuously have no limit to
exceed.

The cost is the ``Content-Length`` header: a size nobody knows yet cannot be
declared, so the browser shows an open-ended progress bar. That is the right trade
against a download that fails outright.

``zipfile`` supports exactly this. Handed an output object with no ``seek``, it
writes each entry's size in a trailing data descriptor instead of going back to
patch the header — the same mechanism every streaming ZIP uses, and ordinary
unzip tools read the result.

**The body must be an async iterator, and that is not a style choice.** This
platform serves ASGI, and :meth:`StreamingHttpResponse.__aiter__` — which is what
``ASGIHandler`` consumes — handles a *sync* iterator by running
``await sync_to_async(list)(...)`` over it. The whole archive is collected into a
list in memory before one body byte goes out: every property this module is built
for, undone silently, by a response that still looks like it streams. A sync
generator here cost an ``ERR_INCOMPLETE_CHUNKED_ENCODING`` once already — headers
sent, then the worker gone under the weight of a video archive held in the heap.
:func:`_astream` is the whole of the remedy, and ``response.is_async`` is the thing
to assert about it.
"""

from __future__ import annotations

import zipfile
from collections.abc import AsyncIterator, Generator, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.core.files.storage import default_storage
from django.http import StreamingHttpResponse

__all__ = ["ArchiveMember", "zip_response"]

#: Read size when copying one stored file into the archive. Also how often the
#: response yields, and so how long a proxy ever waits between bytes.
_COPY_CHUNK_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    """One entry: the name it takes inside the archive, and the stored file behind it."""

    arcname: str
    reference: str


class _Sink:
    """What ``zipfile`` writes into: a buffer the response drains and forwards.

    Deliberately has no ``seek``. ``ZipFile`` probes for one and falls back to data
    descriptors when it is absent, which is what makes a ZIP writable in one pass;
    adding ``seek`` here would silently restore the rewind-and-patch behaviour and
    with it the need to hold the whole archive.
    """

    __slots__ = ("_chunks", "_written")

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._written = 0

    def write(self, data: bytes) -> int:
        self._chunks.append(bytes(data))
        self._written += len(data)
        return len(data)

    def flush(self) -> None:
        """Nothing beneath to flush to; the response drains this instead."""

    def close(self) -> None:
        """Part of the shape ``ZipFile`` accepts. It never calls this on a file it was
        handed rather than opened, and there is nothing to release in any case."""

    def tell(self) -> int:
        """Offset in the archive. ``ZipFile`` needs it to lay out the central directory."""
        return self._written

    def drain(self) -> bytes:
        """Everything written since the last call, and nothing is kept afterwards."""
        if not self._chunks:
            return b""
        payload = b"".join(self._chunks)
        self._chunks.clear()
        return payload


def _storage_key(reference: str) -> str:
    """The key ``default_storage`` knows a file by, given how the edge stored it.

    References are opaque by design, but the ones this platform mints are plain
    keys; anything already absolute (a bucket URL from an older upload) is left
    alone and simply fails the existence check below rather than being mangled.
    """
    return (reference or "").strip()


def _unique(arcname: str, taken: set[str]) -> str:
    """A name no other member has yet, by numbering the collisions.

    Two acts can legitimately submit a file with the same name, and a ZIP with
    duplicate entries is a ZIP some tools unpack to one file.
    """
    if arcname not in taken:
        taken.add(arcname)
        return arcname
    path = PurePosixPath(arcname)
    stem, suffix = path.stem, path.suffix
    parent = str(path.parent) if str(path.parent) != "." else ""
    for index in range(2, 1000):
        candidate = f"{stem} ({index}){suffix}"
        full = f"{parent}/{candidate}" if parent else candidate
        if full not in taken:
            taken.add(full)
            return full
    taken.add(arcname)
    return arcname


def _members(
    members: Sequence[ArchiveMember],
    notes: Iterable[str],
    notes_name: str,
) -> Generator[bytes]:
    """The bytes of the archive, in the order they can be sent.

    A member whose file is missing from storage is skipped rather than fatal: one
    lost upload must not cost the organizer the other two hundred. They are listed
    in ``notes`` at the end, which is exactly what the person downloading has to
    chase — and that list can only be written last, because it is not known until
    every member has been tried.
    """
    sink = _Sink()
    taken: set[str] = set()
    skipped: list[str] = []

    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            key = _storage_key(member.reference)
            if not key or not default_storage.exists(key):
                skipped.append(member.arcname)
                continue
            # ``force_zip64``: writing into a stream means the entry's size is unknown
            # when its header goes out, and without the 64-bit fields a single file over
            # 4 GB would raise here instead of being archived.
            with (
                default_storage.open(key, "rb") as source,
                archive.open(_unique(member.arcname, taken), "w", force_zip64=True) as target,
            ):
                for chunk in iter(lambda source=source: source.read(_COPY_CHUNK_BYTES), b""):  # type: ignore[misc]
                    target.write(chunk)
                    if payload := sink.drain():
                        yield payload
            if payload := sink.drain():
                yield payload
        lines = [*notes, *(f"Файл не найден в хранилище: {name}" for name in skipped)]
        if lines:
            archive.writestr(notes_name, "\n".join(lines) + "\n")
            if payload := sink.drain():
                yield payload
    # Closing wrote the central directory - the part that makes it a readable archive.
    if payload := sink.drain():
        yield payload


def _next_chunk(chunks: Iterator[bytes]) -> bytes | None:
    """The next chunk, or ``None`` once the archive is complete.

    ``None`` as the end marker rather than a sentinel object: :func:`_members` never
    yields an empty chunk - it checks before every yield - so there is nothing to
    confuse it with.
    """
    return next(chunks, None)


async def _astream(chunks: Generator[bytes]) -> AsyncIterator[bytes]:
    """The archive, pulled one chunk at a time off the thread that builds it.

    Reading storage and deflating are blocking work, so each step is handed to a
    worker thread - but *one step at a time*, which is what keeps the response
    incremental. Collecting the generator first would be simpler and would be the
    very thing this module exists to avoid.

    ``thread_sensitive=False`` on purpose. The sensitive variant funnels every call
    through one process-wide thread, and this one occupies its thread for as long as
    the download lasts - which for a festival's video archive is minutes. Every other
    piece of sync work in the process would queue behind it.
    """
    advance = sync_to_async(_next_chunk, thread_sensitive=False)
    try:
        while (chunk := await advance(chunks)) is not None:
            yield chunk
    finally:
        # The client went away mid-download, most likely. Closing here runs the
        # generator's own ``with`` blocks rather than leaving an open storage handle
        # for the collector to find later.
        chunks.close()


def zip_response(
    members: Sequence[ArchiveMember],
    *,
    filename: str,
    notes: Iterable[str] = (),
    notes_name: str = "ПРОЧТИ.txt",
) -> StreamingHttpResponse:
    """Assemble ``members`` into a ZIP and stream it as a download."""
    response = StreamingHttpResponse(
        _astream(_members(members, notes, notes_name)),
        content_type="application/zip",
    )
    # ``filename*`` carries the real, Cyrillic name; the ASCII ``filename`` is the
    # fallback for clients that ignore RFC 5987.
    response["Content-Disposition"] = f"attachment; filename=\"archive.zip\"; filename*=UTF-8''{quote(filename)}"
    # Assembled from whatever is stored *now*, at one unchanging URL. Nothing about the
    # URL says the contents moved, so the only safe answer to "may I reuse this?" is no —
    # otherwise a participant whose diploma was re-issued keeps downloading the old one.
    response["Cache-Control"] = "no-store"
    return response
