"""Streaming a set of stored files out of an endpoint as one ZIP download.

A technical helper, not a bounded context: it knows about storage and HTTP and
nothing else, which is why it sits beside :mod:`config.middleware` rather than
inside any one app. Two edges compose archives out of the same stored files —
the programme's backing tracks and the organizer's paperwork — and neither
should own the other's copy of this.

The archive is spooled, never buffered whole. A festival's backing tracks run to
gigabytes, and a ``BytesIO`` would hold all of it (twice, on ``getvalue()``)
before the first byte reached the client. Small archives stay in memory; large
ones roll over to disk, and the response streams from there.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from urllib.parse import quote

from django.core.files.storage import default_storage
from django.http import FileResponse

__all__ = ["ArchiveMember", "zip_response"]

#: How much of an archive is held in memory before the spool rolls over to disk.
_SPOOL_BYTES = 4 * 1024 * 1024

#: Read size when copying one stored file into the archive.
_COPY_CHUNK_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    """One entry: the name it takes inside the archive, and the stored file behind it."""

    arcname: str
    reference: str


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


def zip_response(
    members: Sequence[ArchiveMember],
    *,
    filename: str,
    notes: Iterable[str] = (),
    notes_name: str = "ПРОЧТИ.txt",
) -> FileResponse:
    """Assemble ``members`` into a ZIP and return it as a streaming download.

    A member whose file is missing from storage is skipped rather than fatal: one
    lost upload must not cost the organizer the other two hundred. ``notes`` are
    written into a small text member — what the archive could not include, which
    is exactly what the person downloading it needs to chase.
    """
    # Not a context manager on purpose: the spool has to outlive this function. The
    # response streams from it and closes it when the last byte has gone out.
    spool = SpooledTemporaryFile(max_size=_SPOOL_BYTES)  # noqa: SIM115
    taken: set[str] = set()
    skipped: list[str] = []

    with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            key = _storage_key(member.reference)
            if not key or not default_storage.exists(key):
                skipped.append(member.arcname)
                continue
            with default_storage.open(key, "rb") as source, archive.open(_unique(member.arcname, taken), "w") as target:
                for chunk in iter(lambda source=source: source.read(_COPY_CHUNK_BYTES), b""):  # type: ignore[misc]
                    target.write(chunk)
        lines = [*notes, *(f"Файл не найден в хранилище: {name}" for name in skipped)]
        if lines:
            archive.writestr(notes_name, "\n".join(lines) + "\n")

    spool.seek(0)
    response = FileResponse(spool, content_type="application/zip")
    # ``filename*`` carries the real, Cyrillic name; the ASCII ``filename`` is the
    # fallback for clients that ignore RFC 5987.
    response["Content-Disposition"] = f"attachment; filename=\"archive.zip\"; filename*=UTF-8''{quote(filename)}"
    return response
